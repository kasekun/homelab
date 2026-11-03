package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var dockerProfilesCmd = &cobra.Command{
	Use:     "profiles",
	Short:   "List all profiles defined in the docker compose configuration",
	Args:    cobra.NoArgs,
	Example: `  jdc docker profiles`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := loadComposeServices()
		if err != nil {
			return fmt.Errorf("listing profiles: %w", err)
		}
		for _, p := range profilesFromServices(services) {
			fmt.Println(p)
		}
		return nil
	},
}

func init() {
	dockerCmd.AddCommand(dockerProfilesCmd)
}
