package cmd

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

var dockerDoctorCmd = &cobra.Command{
	Use:     "doctor",
	Short:   "Validate jdc docker profile and cache metadata",
	Args:    cobra.NoArgs,
	Example: `  jdc docker doctor`,
	RunE: func(cmd *cobra.Command, args []string) error {
		services, err := loadComposeServices()
		if err != nil {
			return fmt.Errorf("loading compose services: %w", err)
		}

		var issues []string
		var warnings []string

		for _, name := range serviceNames(services) {
			svc := services[name]
			if len(svc.Profiles) == 0 {
				issues = append(issues, fmt.Sprintf("service %q has no profiles", name))
				continue
			}
			if !hasString(svc.Profiles, "all") {
				issues = append(issues, fmt.Sprintf("service %q is missing profile %q", name, "all"))
			}
			if svc.ContainerName != "" && svc.ContainerName != name {
				warnings = append(warnings, fmt.Sprintf("service %q uses container_name %q", name, svc.ContainerName))
			}
		}

		cache, err := loadCache(repoRoot)
		if err != nil {
			warnings = append(warnings, fmt.Sprintf("could not read cache: %v", err))
		} else {
			servicesList := serviceNames(services)
			profilesList := profilesFromServices(services)
			if len(cache.Services) == 0 && len(cache.Profiles) == 0 {
				warnings = append(warnings, "cache is empty or missing; run 'jdc self refresh'")
			} else {
				if !sameStrings(cache.Services, servicesList) {
					warnings = append(warnings, "cached services are stale; run 'jdc self refresh'")
				}
				if !sameStrings(cache.Profiles, profilesList) {
					warnings = append(warnings, "cached profiles are stale; run 'jdc self refresh'")
				}
			}
		}

		for _, warning := range warnings {
			fmt.Fprintf(os.Stderr, "WARN: %s\n", warning)
		}
		if len(issues) > 0 {
			for _, issue := range issues {
				fmt.Fprintf(os.Stderr, "ERROR: %s\n", issue)
			}
			return fmt.Errorf("docker doctor found %d issue(s)", len(issues))
		}

		fmt.Printf("docker doctor: OK (%d services, profiles: %s)\n", len(services), strings.Join(profilesFromServices(services), ", "))
		return nil
	},
}

func sameStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func init() {
	dockerCmd.AddCommand(dockerDoctorCmd)
}
