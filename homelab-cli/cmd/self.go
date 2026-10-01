package cmd

import (
	"fmt"
	"sort"
	"strings"

	"github.com/spf13/cobra"
)

var selfCmd = &cobra.Command{
	Use:   "self",
	Short: "Manage the jdc CLI itself (cache, completions)",
}

var selfRefreshCmd = &cobra.Command{
	Use:   "refresh",
	Short: "Rebuild .jdc-cache.json from the current compose configuration",
	Args:  cobra.NoArgs,
	Example: `  jdc self refresh`,
	RunE: func(cmd *cobra.Command, args []string) error {
		logInfo("Refreshing cache at %s...", cachePath(repoRoot))

		servicesOut, err := composeOutput("--profile", "all", "config", "--services")
		if err != nil {
			return fmt.Errorf("querying services: %w", err)
		}
		profilesOut, err := composeOutput("--profile", "all", "config", "--profiles")
		if err != nil {
			return fmt.Errorf("querying profiles: %w", err)
		}

		services := strings.Fields(servicesOut)
		profiles := strings.Fields(profilesOut)
		sort.Strings(services)
		sort.Strings(profiles)

		cache := &jdcCache{
			Services: services,
			Profiles: profiles,
		}
		if err := saveCache(repoRoot, cache); err != nil {
			return fmt.Errorf("writing cache: %w", err)
		}

		logInfo("Cache written: %d service(s), %d profile(s)", len(services), len(profiles))
		return nil
	},
}

// selfCompletionCmd re-parents cobra's built-in completion command under selfCmd
// so all self-management lives in one namespace.
var selfCompletionCmd = &cobra.Command{
	Use:                   "completion [bash|zsh|fish|powershell]",
	Short:                 "Generate shell completion script",
	DisableFlagsInUseLine: true,
	ValidArgs:             []string{"bash", "zsh", "fish", "powershell"},
	Args:                  cobra.MatchAll(cobra.ExactArgs(1), cobra.OnlyValidArgs),
	Example: `  jdc self completion zsh
  jdc self completion bash`,
	RunE: func(cmd *cobra.Command, args []string) error {
		switch args[0] {
		case "bash":
			return rootCmd.GenBashCompletion(cmd.OutOrStdout())
		case "zsh":
			return rootCmd.GenZshCompletion(cmd.OutOrStdout())
		case "fish":
			return rootCmd.GenFishCompletion(cmd.OutOrStdout(), true)
		case "powershell":
			return rootCmd.GenPowerShellCompletionWithDesc(cmd.OutOrStdout())
		default:
			return fmt.Errorf("unsupported shell %q", args[0])
		}
	},
}

func init() {
	selfCmd.AddCommand(selfRefreshCmd)
	selfCmd.AddCommand(selfCompletionCmd)
	rootCmd.AddCommand(selfCmd)
}
