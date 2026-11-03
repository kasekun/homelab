package cmd

import (
	"fmt"
	"os/exec"

	"github.com/spf13/cobra"
)

var removeServices []string
var removeVolumes bool
var removeYes bool

var dockerRemoveCmd = &cobra.Command{
	Use:   "remove",
	Short: "Remove containers (with docker rm -f fallback for orphans)",
	Args:  cobra.NoArgs,
	Example: `  jdc docker remove -s sonarr
  jdc docker remove -s orphan-container
  jdc docker remove -p media --yes`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(removeServices)
		if err != nil {
			return err
		}
		if len(services) == 0 {
			return fmt.Errorf("for 'docker remove', target one or more services with -s or a profile with -p")
		}
		if len(removeServices) == 0 && profileFlag != "" && !removeYes && !resolveOnly {
			return fmt.Errorf("refusing to remove all containers in profile %q without --yes", profileFlag)
		}

		for _, svc := range services {
			logInfo("Removing container: %s", svc)
			composeArgs := []string{"rm", "-sf"}
			if removeVolumes {
				composeArgs = append(composeArgs, "-v")
			}
			composeArgs = append(composeArgs, svc)
			if err := runCompose(composeArgs...); err != nil {
				logInfo("%q was not removed by compose; trying direct docker rm -f", svc)
				dockerArgs := []string{"rm", "-f"}
				if removeVolumes {
					dockerArgs = append(dockerArgs, "-v")
				}
				dockerArgs = append(dockerArgs, svc)
				if fallbackErr := exec.Command("docker", dockerArgs...).Run(); fallbackErr != nil {
					logInfo("WARN: could not remove container %q: %v", svc, fallbackErr)
				}
			}
		}
		return nil
	},
}

func init() {
	addServiceFlag(dockerRemoveCmd, &removeServices)
	dockerRemoveCmd.Flags().BoolVar(&removeVolumes, "volumes", false, "remove anonymous volumes attached to containers")
	dockerRemoveCmd.Flags().BoolVarP(&removeYes, "yes", "y", false, "confirm profile-wide removal")
	dockerCmd.AddCommand(dockerRemoveCmd)
}
