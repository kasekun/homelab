package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var dockerContainersCmd = &cobra.Command{
	Use:     "containers",
	Short:   "List all services defined in the docker compose configuration",
	Args:    cobra.NoArgs,
	Example: `  jdc docker containers`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := loadComposeServices()
		if err != nil {
			return fmt.Errorf("listing containers: %w", err)
		}
		for _, svc := range serviceNames(services) {
			fmt.Println(svc)
		}
		return nil
	},
}

func init() {
	dockerCmd.AddCommand(dockerContainersCmd)
}
