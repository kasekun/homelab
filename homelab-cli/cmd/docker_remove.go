package cmd

import (
	"fmt"
	"os/exec"

	"github.com/spf13/cobra"
)

var removeServices []string

var dockerRemoveCmd = &cobra.Command{
	Use:   "remove",
	Short: "Remove containers (with docker rm -f fallback for orphans)",
	Args:  cobra.NoArgs,
	Example: `  jdc docker remove -s sonarr
  jdc docker remove -s orphan-container`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(removeServices)
		if err != nil {
			return err
		}
		if len(services) == 0 {
			return fmt.Errorf("at least one -s service flag is required for remove")
		}

		for _, svc := range services {
			logInfo("Removing container: %s", svc)
			if err := runCompose("rm", "-f", svc); err != nil {
				logInfo("%q not found in compose project; trying direct docker rm -f", svc)
				if fallbackErr := exec.Command("docker", "rm", "-f", svc).Run(); fallbackErr != nil {
					logInfo("WARN: could not remove container %q: %v", svc, fallbackErr)
				}
			}
		}
		return nil
	},
}

func init() {
	addServiceFlag(dockerRemoveCmd, &removeServices)
	dockerCmd.AddCommand(dockerRemoveCmd)
}
