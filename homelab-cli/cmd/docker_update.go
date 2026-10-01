package cmd

import (
	"github.com/spf13/cobra"
)

var updateServices []string

var dockerUpdateCmd = &cobra.Command{
	Use:   "update",
	Short: "Pull the latest images and restart services (pull then up -d)",
	Args:  cobra.NoArgs,
	Example: `  jdc docker update -s sonarr
  jdc docker update -p media`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(updateServices)
		if err != nil {
			return err
		}

		pullArgs := append([]string{"pull"}, services...)
		if err := runCompose(pullArgs...); err != nil {
			return err
		}

		upArgs := append([]string{"up", "-d"}, services...)
		return runCompose(upArgs...)
	},
}

func init() {
	addServiceFlag(dockerUpdateCmd, &updateServices)
	dockerCmd.AddCommand(dockerUpdateCmd)
}
