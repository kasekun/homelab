package cmd

import (
	"github.com/spf13/cobra"
)

var restartServices []string

var dockerRestartCmd = &cobra.Command{
	Use:   "restart",
	Short: "Restart services",
	Args:  cobra.NoArgs,
	Example: `  jdc docker restart -s sonarr
  jdc docker restart -p core`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(restartServices)
		if err != nil {
			return err
		}
		composeArgs := []string{"restart"}
		composeArgs = append(composeArgs, services...)
		return runCompose(composeArgs...)
	},
}

func init() {
	addServiceFlag(dockerRestartCmd, &restartServices)
	dockerCmd.AddCommand(dockerRestartCmd)
}
