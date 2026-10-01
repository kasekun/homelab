package cmd

import (
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
)

var getIPServices []string

var dockerGetIPCmd = &cobra.Command{
	Use:   "get-ip",
	Short: "Show the external IP address for a container",
	Args:  cobra.NoArgs,
	Example: `  jdc docker get-ip -s qbittorrent`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(getIPServices) == 0 {
			return fmt.Errorf("at least one -s service flag is required for get-ip")
		}

		for _, svc := range getIPServices {
			logInfo("Checking external IP for container: %s", svc)
			out, err := exec.Command("docker", "exec", svc, "curl", "--silent", "http://ipinfo.io/ip").Output()
			if err != nil {
				fmt.Printf("[ERROR] Failed to execute docker exec for container %q: %v\n", svc, err)
				continue
			}

			extIP := strings.TrimSpace(string(out))
			if extIP == "" {
				fmt.Printf("[ERROR] No IP returned for container %q\n", svc)
				continue
			}

			fmt.Printf("%s container's external IP address: %s\n", svc, extIP)
			fmt.Println("IP info:")

			resp, err := http.Get("http://ipinfo.io/" + extIP)
			if err != nil {
				fmt.Printf("[ERROR] Could not fetch ipinfo.io for %s: %v\n", extIP, err)
				continue
			}
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			fmt.Println(string(body))
		}
		return nil
	},
}

func init() {
	addServiceFlag(dockerGetIPCmd, &getIPServices)
	dockerCmd.AddCommand(dockerGetIPCmd)
}
