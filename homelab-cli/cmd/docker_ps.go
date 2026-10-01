package cmd

import (
	"github.com/spf13/cobra"
)

var dockerPsCmd = &cobra.Command{
	Use:     "ps",
	Short:   "Show service status and ports",
	Args:    cobra.NoArgs,
	Example: `  jdc docker ps`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runCompose("ps", "--format", "table {{.Name}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}")
	},
}

func init() {
	dockerCmd.AddCommand(dockerPsCmd)
}
