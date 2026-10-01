package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

const logRetryWindow = 2 * time.Minute

var logsServices []string

var dockerLogsCmd = &cobra.Command{
	Use:   "logs",
	Short: "Tail logs for all services or specific services",
	Args:  cobra.NoArgs,
	Example: `  jdc docker logs
  jdc docker logs -s sonarr
  jdc docker logs -s sonarr -s radarr
  jdc docker logs -p media`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(logsServices)
		if err != nil {
			return err
		}

		composeArgs := []string{"logs", "-ft"}
		composeArgs = append(composeArgs, services...)

		// Without named services or in resolve-only mode, run once and return.
		if len(services) == 0 || resolveOnly {
			return runCompose(composeArgs...)
		}

		// Named service(s): wait for at least one to be up, then follow logs.
		// If the stream stops, wait up to logRetryWindow for restart before re-attaching.
		if err := waitForAnyService(services, time.Time{}); err != nil {
			return err
		}

		for {
			err := runCompose(composeArgs...)
			if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 130 {
				return nil
			}
			fmt.Fprintln(os.Stderr)
			if err != nil {
				logInfo("Log stream exited: %v", err)
			} else {
				logInfo("%s stopped.", strings.Join(services, ", "))
			}

			deadline := time.Now().Add(logRetryWindow)
			logInfo("Waiting up to %s for service(s) to restart...", logRetryWindow)

			if err := waitForAnyService(services, deadline); err != nil {
				return fmt.Errorf("service(s) did not restart within %s", logRetryWindow)
			}

			logInfo("Service(s) running, re-attaching logs...")
		}
	},
}

func init() {
	addServiceFlag(dockerLogsCmd, &logsServices)
	dockerCmd.AddCommand(dockerLogsCmd)
}

// waitForAnyService polls until at least one named compose service has a running container.
// It uses exponential backoff between checks (1s → 2s → 4s → … capped at 16s).
// If deadline is non-zero, it returns an error once the deadline is exceeded.
func waitForAnyService(services []string, deadline time.Time) error {
	delay := time.Second
	for {
		for _, svc := range services {
			psOut, err := composeOutput("ps", "-q", svc)
			if err == nil {
				for _, id := range strings.Fields(psOut) {
					out, err := exec.Command("docker", "inspect", "-f", "{{.State.Running}}", id).Output()
					if err == nil && strings.TrimSpace(string(out)) == "true" {
						return nil
					}
				}
			}
		}

		if !deadline.IsZero() && time.Now().After(deadline) {
			return fmt.Errorf("timed out waiting for service(s) to start")
		}

		logInfo("Waiting for service(s) to start...")
		time.Sleep(delay)
		if delay < 16*time.Second {
			delay *= 2
		}
	}
}
