package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
)

var downYes bool

type composePSContainer struct {
	Name    string `json:"Name"`
	Service string `json:"Service"`
	State   string `json:"State"`
	Status  string `json:"Status"`
}

var dockerDownCmd = &cobra.Command{
	Use:   "down",
	Short: "Stop and remove all containers and networks (full project teardown)",
	Long: `Tears down the entire project. Does not accept -s or -p targeting.
Use 'jdc docker stop -p all' if non-destructive stop behavior is required.`,
	Args: cobra.NoArgs,
	Example: `  jdc docker down
  jdc docker down --yes`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if profileFlag != "" {
			return fmt.Errorf("'docker down' is always a full project teardown and does not accept -p/--profile")
		}
		containers, err := projectContainers()
		if err != nil {
			return err
		}
		printDownWarning(containers)
		if !downYes && !resolveOnly {
			if err := confirmDown(); err != nil {
				return err
			}
		}
		return runCompose("down", "--remove-orphans")
	},
}

func projectContainers() ([]composePSContainer, error) {
	out, err := composeOutput("ps", "--all", "--format", "json")
	if err != nil {
		return nil, fmt.Errorf("listing project containers: %w", err)
	}
	return parseComposePSContainers(out)
}

func parseComposePSContainers(out string) ([]composePSContainer, error) {
	var containers []composePSContainer
	for _, line := range strings.Split(strings.TrimSpace(out), "\n") {
		if line == "" {
			continue
		}
		var container composePSContainer
		if err := json.Unmarshal([]byte(line), &container); err != nil {
			return nil, err
		}
		containers = append(containers, container)
	}
	return containers, nil
}

func printDownWarning(containers []composePSContainer) {
	fmt.Fprintln(os.Stderr, "This will stop and remove these project containers:")
	if len(containers) == 0 {
		fmt.Fprintln(os.Stderr, "  (none currently reported by docker compose ps --all)")
	}
	for _, container := range containers {
		status := container.Status
		if status == "" {
			status = container.State
		}
		fmt.Fprintf(os.Stderr, "  - %s (%s, %s)\n", container.Name, container.Service, status)
	}
	fmt.Fprintln(os.Stderr, "Use 'jdc docker stop -p all' to stop services without removing containers.")
}

func confirmDown() error {
	fmt.Fprint(os.Stderr, "Continue? [y/N]: ")
	answer, err := readSingleKey()
	if err != nil {
		return fmt.Errorf("reading confirmation: %w", err)
	}
	if !isYesByte(answer) {
		return fmt.Errorf("cancelled")
	}
	return nil
}

func readSingleKey() (byte, error) {
	restore, raw := enableRawInput()
	if raw {
		defer func() {
			restore()
			fmt.Fprintln(os.Stderr)
		}()
	}

	var answer [1]byte
	n, err := os.Stdin.Read(answer[:])
	if err != nil {
		return 0, err
	}
	if n == 0 {
		return 0, io.EOF
	}
	return answer[0], nil
}

func enableRawInput() (func(), bool) {
	stateCmd := exec.Command("stty", "-g")
	stateCmd.Stdin = os.Stdin
	stateOut, err := stateCmd.Output()
	if err != nil {
		return nil, false
	}
	state := strings.TrimSpace(string(stateOut))

	rawCmd := exec.Command("stty", "raw", "-echo")
	rawCmd.Stdin = os.Stdin
	if err := rawCmd.Run(); err != nil {
		return nil, false
	}

	return func() {
		restoreCmd := exec.Command("stty", state)
		restoreCmd.Stdin = os.Stdin
		_ = restoreCmd.Run()
	}, true
}

func isYesByte(answer byte) bool {
	return answer == 'y' || answer == 'Y'
}

func init() {
	dockerDownCmd.Flags().BoolVarP(&downYes, "yes", "y", false, "confirm full project teardown")
	dockerCmd.AddCommand(dockerDownCmd)
}
