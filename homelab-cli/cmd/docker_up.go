package cmd

import (
	"github.com/spf13/cobra"
)

var upServices []string

var dockerUpCmd = &cobra.Command{
	Use:   "up",
	Short: "Start services detached (optionally targeting specific services or a profile)",
	Args:  cobra.NoArgs,
	Example: `  jdc docker up
  jdc docker up -s sonarr -s radarr
  jdc docker up -p core`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(upServices)
		if err != nil {
			return err
		}
		composeArgs := []string{"up", "-d"}
		composeArgs = append(composeArgs, services...)
		return runCompose(composeArgs...)
	},
}

func init() {
	addServiceFlag(dockerUpCmd, &upServices)
	dockerCmd.AddCommand(dockerUpCmd)
}
