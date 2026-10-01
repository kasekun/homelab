package cmd

import (
	"fmt"
	"sort"
	"strings"

	"github.com/spf13/cobra"
)

var dockerProfilesCmd = &cobra.Command{
	Use:     "profiles",
	Short:   "List all profiles defined in the docker compose configuration",
	Args:    cobra.NoArgs,
	Example: `  jdc docker profiles`,
	RunE: func(cmd *cobra.Command, args []string) error {
		out, err := composeOutput("--profile", "all", "config", "--profiles")
		if err != nil {
			return fmt.Errorf("listing profiles: %w", err)
		}
		profiles := strings.Fields(out)
		sort.Strings(profiles)
		for _, p := range profiles {
			fmt.Println(p)
		}
		return nil
	},
}

func init() {
	dockerCmd.AddCommand(dockerProfilesCmd)
}
