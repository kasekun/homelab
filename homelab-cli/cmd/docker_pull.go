package cmd

import (
	"github.com/spf13/cobra"
)

var pullServices []string

var dockerPullCmd = &cobra.Command{
	Use:   "pull",
	Short: "Pull the latest images without restarting",
	Args:  cobra.NoArgs,
	Example: `  jdc docker pull -s sonarr
  jdc docker pull -p media`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := resolveServices(pullServices)
		if err != nil {
			return err
		}
		composeArgs := []string{"pull"}
		composeArgs = append(composeArgs, services...)
		return runCompose(composeArgs...)
	},
}

func init() {
	addServiceFlag(dockerPullCmd, &pullServices)
	dockerCmd.AddCommand(dockerPullCmd)
}
