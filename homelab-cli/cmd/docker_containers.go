package cmd

import (
	"fmt"
	"sort"
	"strings"

	"github.com/spf13/cobra"
)

var dockerContainersCmd = &cobra.Command{
	Use:     "containers",
	Short:   "List all services defined in the docker compose configuration",
	Args:    cobra.NoArgs,
	Example: `  jdc docker containers`,
	RunE: func(cmd *cobra.Command, args []string) error {
		out, err := composeOutput("--profile", "all", "config", "--services")
		if err != nil {
			return fmt.Errorf("listing containers: %w", err)
		}
		services := strings.Fields(out)
		sort.Strings(services)
		for _, svc := range services {
			fmt.Println(svc)
		}
		return nil
	},
}

func init() {
	dockerCmd.AddCommand(dockerContainersCmd)
}
