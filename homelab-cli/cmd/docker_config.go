package cmd

import (
	"github.com/spf13/cobra"
)

var configServices []string

var dockerConfigCmd = &cobra.Command{
	Use:   "config",
	Short: "Print the resolved docker compose configuration",
	Args:  cobra.NoArgs,
	Example: `  jdc docker config
  jdc docker config -p core`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(configServices)
		if err != nil {
			return err
		}
		composeArgs := []string{"config"}
		composeArgs = append(composeArgs, services...)
		return runCompose(composeArgs...)
	},
}

func init() {
	addServiceFlag(dockerConfigCmd, &configServices)
	dockerCmd.AddCommand(dockerConfigCmd)
}
