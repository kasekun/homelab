package cmd

import (
	"github.com/spf13/cobra"
)

var dockerDownCmd = &cobra.Command{
	Use:   "down",
	Short: "Stop and remove all containers and networks (full project teardown)",
	Long: `Tears down the entire project. Does not accept -s or -p targeting.
For selective teardown, use 'jdc docker stop' followed by 'jdc docker remove'.`,
	Args:    cobra.NoArgs,
	Example: `  jdc docker down`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runCompose("down", "--remove-orphans")
	},
}

func init() {
	dockerCmd.AddCommand(dockerDownCmd)
}
