package cmd

import (
	"github.com/spf13/cobra"
)

var stopServices []string

var dockerStopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop services without removing them",
	Args:  cobra.NoArgs,
	Example: `  jdc docker stop -s sonarr
  jdc docker stop -p media`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(stopServices)
		if err != nil {
			return err
		}
		composeArgs := []string{"stop"}
		composeArgs = append(composeArgs, services...)
		return runCompose(composeArgs...)
	},
}

func init() {
	addServiceFlag(dockerStopCmd, &stopServices)
	dockerCmd.AddCommand(dockerStopCmd)
}
