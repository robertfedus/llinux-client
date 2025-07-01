import os
import re
import subprocess
import platform
import shutil
from pathlib import Path

class CommandExecutor:    
    @staticmethod
    def run_command(command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            return ""
        

class SystemInformation:
    
    def __init__(self):
        self.executor = CommandExecutor()

    def get_distribution(self):

        if os.path.exists("/etc/os-release"):
            os_release = self.executor.run_command("cat /etc/os-release")
            
            pretty_name_match = re.search(r'PRETTY_NAME="([^"]+)"', os_release)
            if pretty_name_match:
                return pretty_name_match.group(1)
            
            name_match = re.search(r'NAME="([^"]+)"', os_release)
            version_match = re.search(r'VERSION="([^"]+)"', os_release)
            
            if name_match:
                name = name_match.group(1)
                version = version_match.group(1) if version_match else ""
                return f"{name} {version}".strip()
        
        if os.path.exists("/etc/lsb-release"):
            lsb_release = self.executor.run_command("cat /etc/lsb-release")
            distro_match = re.search(r'DISTRIB_DESCRIPTION="([^"]+)"', lsb_release)
            if distro_match:
                return distro_match.group(1)
        
        for file_path in ["/etc/redhat-release", "/etc/debian_version", "/etc/SuSE-release", "/etc/arch-release"]:
            if os.path.exists(file_path):
                content = self.executor.run_command(f"cat {file_path}")
                if content:
                    if file_path == "/etc/debian_version":
                        return f"Debian {content}"
                    if file_path == "/etc/arch-release":
                        return "Arch Linux"
                    return content
        
        lsb_release_path = shutil.which("lsb_release")
        if lsb_release_path:
            return self.executor.run_command("lsb_release -ds")
        
        return platform.linux_distribution()[0] if hasattr(platform, 'linux_distribution') else "Unknown Linux Distribution"
    
    def get_package_manager(self):
        package_managers = []
        
        package_manager_cmds = {
            "apt": "APT (Debian/Ubuntu)",
            "apt-get": "APT (Debian/Ubuntu)",
            "dnf": "DNF (Fedora/RHEL/CentOS)",
            "yum": "YUM (RHEL/CentOS/Fedora)",
            "pacman": "Pacman (Arch Linux)",
            "zypper": "Zypper (openSUSE)",
            "apk": "apk (Alpine Linux)",
            "emerge": "Portage (Gentoo)",
            "xbps-install": "XBPS (Void Linux)",
            "flatpak": "Flatpak",
            "snap": "Snap",
        }
        
        for cmd, name in package_manager_cmds.items():
            if shutil.which(cmd):
                package_managers.append(name)
        
        if shutil.which("rpm"):
            if "DNF" not in " ".join(package_managers) and "YUM" not in " ".join(package_managers):
                package_managers.append("RPM")
        
        if shutil.which("dpkg"):
            if "APT" not in " ".join(package_managers):
                package_managers.append("DPKG (Debian-based)")
        
        if shutil.which("nix") or os.path.exists("/nix"):
            package_managers.append("Nix")
        
        return ", ".join(package_managers) if package_managers else "Unknown Package Manager"
    
    def get_bootloader(self):
        if os.path.exists("/boot/grub") or os.path.exists("/boot/grub2"):
            grub_version = self.executor.run_command("grub-install --version 2>/dev/null || grub2-install --version 2>/dev/null")
            if grub_version:
                return f"GRUB ({grub_version.split()[-1]})"
            return "GRUB"
        
        if os.path.exists("/boot/efi/EFI/systemd") or os.path.exists("/boot/efi/EFI/BOOT/systemd-bootx64.efi"):
            return "systemd-boot"
        
        if os.path.exists("/etc/lilo.conf"):
            return "LILO"
        
        if os.path.exists("/sys/firmware/efi"):
            efi_entries = self.executor.run_command("efibootmgr -v 2>/dev/null")
            if "rEFInd" in efi_entries:
                return "rEFInd"
            if efi_entries:
                boot_entry_match = re.search(r'Boot([0-9a-fA-F]+)\* (.+)', efi_entries)
                if boot_entry_match:
                    return f"UEFI ({boot_entry_match.group(2)})"
                return "UEFI"
        
        if os.path.exists("/proc/xen"):
            return "Xen Hypervisor"
        
        dmesg_output = self.executor.run_command("dmesg | grep -i boot")
        if "syslinux" in dmesg_output.lower():
            return "Syslinux"
        
        return "Unknown Package Manager"
    
    def get_init_system(self):
        if os.path.exists("/run/systemd/system") or os.path.exists("/sys/fs/cgroup/systemd"):
            systemd_version = self.executor.run_command("systemctl --version")
            if systemd_version:
                version_match = re.search(r'systemd (\d+)', systemd_version)
                if version_match:
                    return f"systemd (version {version_match.group(1)})"
            return "systemd"
        
        if os.path.exists("/etc/init.d") and os.path.exists("/etc/inittab"):
            return "SysVinit"
        
        if os.path.exists("/etc/init"):
            upstart_version = self.executor.run_command("initctl --version 2>/dev/null")
            if "upstart" in upstart_version.lower():
                version_match = re.search(r'initctl \(upstart ([^)]+)\)', upstart_version)
                if version_match:
                    return f"Upstart (version {version_match.group(1)})"
                return "Upstart"
        
        if os.path.exists("/etc/init.d") and os.path.exists("/etc/rc.conf"):
            openrc_version = self.executor.run_command("rc-status --version 2>/dev/null")
            if openrc_version:
                return f"OpenRC ({openrc_version.split()[-1]})"
            return "OpenRC"
        
        if os.path.exists("/etc/runit") or os.path.exists("/etc/sv"):
            return "runit"
        
        if os.path.exists("/etc/s6") or self.executor.run_command("s6-svscan --help 2>/dev/null"):
            return "s6"
        
        pid1_cmd = self.executor.run_command("cat /proc/1/comm")
        if pid1_cmd:
            return f"PID 1: {pid1_cmd}"
        
        return "Unknown Init System"
    
    def get_kernel_version(self):
        return platform.release()
    
    def get_cpu_info(self):
        cpu_info = self.executor.run_command("cat /proc/cpuinfo | grep 'model name' | head -n1")
        if cpu_info:
            model_match = re.search(r'model name\s*:\s*(.+)', cpu_info)
            if model_match:
                return model_match.group(1)
        
        lscpu_output = self.executor.run_command("lscpu | grep 'Model name'")
        if lscpu_output:
            model_match = re.search(r'Model name:\s*(.+)', lscpu_output)
            if model_match:
                return model_match.group(1)
        
        arch = platform.machine()
        return f"Unknown CPU ({arch})"
    
    def get_gpu_info(self):
        lspci_output = self.executor.run_command("lspci | grep -i 'vga\\|3d\\|display'")
        if lspci_output:
            gpu_lines = []
            for line in lspci_output.split('\n'):
                if any(vendor in line.lower() for vendor in ['nvidia', 'amd', 'ati', 'intel', 'matrox', 'asmedia', 'via', 'silicon']):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        gpu_lines.append(parts[1].strip())
                    else:
                        gpu_lines.append(line.strip())
            
            if gpu_lines:
                return ", ".join(gpu_lines)
        
        if os.path.exists("/sys/class/drm"):
            gpu_nodes = self.executor.run_command("find /sys/class/drm -name 'card*' | sort")
            if gpu_nodes:
                return f"GPU devices found: {gpu_nodes.count('card')}"
        
        glxinfo_output = self.executor.run_command("glxinfo 2>/dev/null | grep 'OpenGL renderer'")
        if glxinfo_output:
            renderer_match = re.search(r'OpenGL renderer string:\s*(.+)', glxinfo_output)
            if renderer_match:
                return renderer_match.group(1)
        
        return "Unknown GPU"
        
    def get_memory_info(self):
        meminfo = self.executor.run_command("cat /proc/meminfo")
        
        ram_total = "Unknown"
        swap_total = "Unknown"
        
        ram_match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
        if ram_match:
            ram_kb = int(ram_match.group(1))
            if ram_kb > 1048576:
                ram_total = f"{ram_kb / 1048576:.2f} GB"
            else:
                ram_total = f"{ram_kb / 1024:.2f} MB"
        
        swap_match = re.search(r'SwapTotal:\s+(\d+)\s+kB', meminfo)
        if swap_match:
            swap_kb = int(swap_match.group(1))
            if swap_kb > 1048576:
                swap_total = f"{swap_kb / 1048576:.2f} GB"
            elif swap_kb > 0:
                swap_total = f"{swap_kb / 1024:.2f} MB"
            else:
                swap_total = "None"
        
        return f"RAM: {ram_total}, Swap: {swap_total}"
    
    def detect_docker(self):
        if os.path.exists("/.dockerenv"):
            return "Running inside Docker container (found /.dockerenv)"
        
        cgroup_content = self.executor.run_command("cat /proc/1/cgroup 2>/dev/null")
        if cgroup_content and ("docker" in cgroup_content or "containerd" in cgroup_content):
            return "Running inside Docker container (detected in cgroups)"
        
        proc_1_cmdline = self.executor.run_command("cat /proc/1/cmdline 2>/dev/null")
        if proc_1_cmdline and "containerd" in proc_1_cmdline:
            return "Running inside container (containerd detected)"
        
        if shutil.which("docker"):
            docker_version = self.executor.run_command("docker --version 2>/dev/null")
            if docker_version:
                return f"Docker installed: {docker_version}"
            return "Docker installed"
        
        return "Docker not detected"
    
    def get_shell_info(self):
        current_shell = os.environ.get("SHELL", "")
        shell_name = os.path.basename(current_shell) if current_shell else "Unknown"
        
        version = ""
        if shell_name == "bash":
            version = self.executor.run_command("bash --version | head -n1")
            if version:
                version_match = re.search(r'version\s+(.+?)[\s,]', version)
                if version_match:
                    version = version_match.group(1)
        elif shell_name == "zsh":
            version = self.executor.run_command("zsh --version")
            if version:
                version_match = re.search(r'zsh\s+(\d+\.\d+[^\s]*)', version)
                if version_match:
                    version = version_match.group(1)
        elif shell_name == "fish":
            version = self.executor.run_command("fish --version")
            if version:
                version_match = re.search(r'fish,\s+version\s+(\d+\.\d+\.\d+)', version)
                if version_match:
                    version = version_match.group(1)
        elif shell_name == "dash":
            version = self.executor.run_command("dpkg -s dash 2>/dev/null | grep Version")
            if version:
                version_match = re.search(r'Version:\s+(.+)', version)
                if version_match:
                    version = version_match.group(1)
        
        if version:
            return f"{shell_name} (version {version})"
        return shell_name
    
    def get_display_manager(self):
        dm_services = {
            "gdm": "GDM (GNOME Display Manager)",
            "gdm3": "GDM3 (GNOME Display Manager 3)",
            "lightdm": "LightDM",
            "sddm": "SDDM (Simple Desktop Display Manager)",
            "xdm": "XDM (X Display Manager)",
            "lxdm": "LXDM (LXDE Display Manager)",
            "slim": "SLiM (Simple Login Manager)",
            "wdm": "WDM (WINGs Display Manager)",
        }
        
        if shutil.which("systemctl"):
            for dm, dm_name in dm_services.items():
                status = self.executor.run_command(f"systemctl is-active {dm}.service 2>/dev/null")
                if status == "active":
                    return dm_name
        
        for dm, dm_name in dm_services.items():
            if os.path.exists(f"/etc/{dm}") or os.path.exists(f"/etc/{dm}.conf"):
                return dm_name
        
        ps_output = self.executor.run_command("ps -e | grep -E 'gdm|lightdm|sddm|xdm|lxdm|slim|wdm'")
        if ps_output:
            for dm, dm_name in dm_services.items():
                if dm in ps_output:
                    return dm_name
        
        if os.path.exists("/etc/X11/default-display-manager"):
            dm_path = self.executor.run_command("cat /etc/X11/default-display-manager")
            if dm_path:
                dm_name = os.path.basename(dm_path)
                for dm, full_name in dm_services.items():
                    if dm == dm_name:
                        return full_name
                return dm_name
        
        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
            return "None (TTY console login)"
        
        return "Unknown Display Manager"
    
    def get_desktop_environment(self):
        desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "")
        if desktop_env:
            if desktop_env.lower() == "hyprland":
                return "Hyprland"
            if desktop_env == "X-Cinnamon":
                return "Cinnamon"
            return desktop_env
        
        de_processes = {
            "gnome-session": "GNOME",
            "kwin": "KDE Plasma",
            "plasma-desktop": "KDE Plasma",
            "xfce4-session": "Xfce",
            "cinnamon-session": "Cinnamon",
            "mate-session": "MATE",
            "lxsession": "LXDE",
            "lxqt-session": "LXQt",
            "budgie-panel": "Budgie",
            "deepin-wm": "Deepin",
            "enlightenment": "Enlightenment",
            "i3": "i3",
            "sway": "Sway",
            "openbox": "Openbox",
            "fluxbox": "Fluxbox",
            "bspwm": "bspwm",
            "awesome": "Awesome WM",
            "icewm": "IceWM",
            "jwm": "JWM",
            "dwm": "dwm",
            "hyprland": "Hyprland",
        }
        
        ps_output = self.executor.run_command("ps -e").lower()
        for process, de_name in de_processes.items():
            if process in ps_output:
                return de_name
        
        session_manager = os.environ.get("SESSION_MANAGER", "")
        if "gnome" in session_manager.lower():
            return "GNOME"
        if "kde" in session_manager.lower():
            return "KDE Plasma"
        
        window_manager = os.environ.get("WINDOW_MANAGER", "")
        if window_manager:
            return os.path.basename(window_manager)
        
        if "DISPLAY" in os.environ or "WAYLAND_DISPLAY" in os.environ:
            if shutil.which("wmctrl"):
                wm_name = self.executor.run_command("wmctrl -m 2>/dev/null | grep 'Name:'")
                if wm_name:
                    name_match = re.search(r'Name:\s+(.+)', wm_name)
                    if name_match:
                        return f"Window Manager: {name_match.group(1)}"
        
        if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
            return "None (TTY console)"
        
        return "Unknown Desktop Environment"
    
    def get_display_server(self):
        if "WAYLAND_DISPLAY" in os.environ:
            compositor = "Unknown Wayland compositor"
            
            if shutil.which("sway"):
                if "sway" in self.executor.run_command("ps -e"):
                    return "Wayland (Sway compositor)"
            
            if "GNOME" in self.get_desktop_environment():
                return "Wayland (Mutter/GNOME Shell compositor)"
            
            if "KDE" in self.get_desktop_environment() or "Plasma" in self.get_desktop_environment():
                return "Wayland (KWin/KDE Plasma compositor)"
            
            if "wlroots" in self.executor.run_command("ps -e aux | grep -i wayland"):
                return "Wayland (wlroots-based compositor)"
            
            return "Wayland"
        
        if "DISPLAY" in os.environ:
            if shutil.which("xprop"):
                compositor_check = self.executor.run_command("xprop -root _NET_SUPPORTING_WM_CHECK")
                if compositor_check:
                    window_id = re.search(r'window id # (0x[0-9a-f]+)', compositor_check)
                    if window_id:
                        wm_name = self.executor.run_command(f"xprop -id {window_id.group(1)} _NET_WM_NAME")
                        if wm_name:
                            name_match = re.search(r'= "(.*)"', wm_name)
                            if name_match:
                                return f"X11 (compositor: {name_match.group(1)})"
            
            x11_compositors = {
                "compiz": "Compiz",
                "compton": "Compton",
                "picom": "Picom",
                "xcompmgr": "Xcompmgr",
                "kwin": "KWin",
                "xfwm4": "Xfwm4",
                "metacity": "Metacity",
                "mutter": "Mutter",
                "marco": "Marco",
                "openbox": "Openbox",
                "fluxbox": "Fluxbox",
                "i3": "i3",
                "awesome": "Awesome WM",
                "dwm": "dwm",
            }
            
            ps_output = self.executor.run_command("ps -e")
            for process, compositor_name in x11_compositors.items():
                if process in ps_output:
                    return f"X11 (compositor: {compositor_name})"
            
            return "X11 (unknown compositor)"
        
        return "No display server detected (console mode)"
    

    def get_uptime(self):
        raw = self.executor.run_command("uptime -p")
        return raw.replace("up ", "").strip()

    def get_cpu_load(self):
        try:
            return self.executor.run_command("echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]")
            
        except Exception:
            return "Unknown"


    def get_memory_load(self):
        raw = self.executor.run_command("free -h")
        lines = raw.splitlines()
        mem_line = next((line for line in lines if line.lower().startswith("mem")), None)
        if mem_line:
            parts = mem_line.split()
            used = parts[2]
            total = parts[1]
            return f"{used}/{total}"
        return "Unknown"

    def get_disk_load(self):
        raw = self.executor.run_command("df -BG / | grep /")
        parts = raw.split()
        if len(parts) >= 3:
            used = parts[2]
            total = parts[1]
            return f"{used}/{total}"
        return "Unknown"

    def get_hostname(self):
        hostname = self.executor.run_command("cat /proc/sys/kernel/hostname")
        if hostname:
            return hostname.strip()

        hostname = self.executor.run_command("cat /etc/hostname")
        if hostname:
            return hostname.strip()

        hostname = self.executor.run_command("uname -n")
        return hostname.strip() if hostname else "Unknown"

    
    def collect_all_info(self):
        return {
            "hostname": self.get_hostname(),
            "linux_distribution": self.get_distribution(),
            "package_manager": self.get_package_manager(),
            "bootloader": self.get_bootloader(),
            "init_system": self.get_init_system(),
            "kernel_version": self.get_kernel_version(),
            "cpu": self.get_cpu_info(),
            "gpu": self.get_gpu_info(), 
            "memory": self.get_memory_info(),
            "is_docker_installed": self.detect_docker(),
            "shell": self.get_shell_info(),
            "display_manager": self.get_display_manager(),
            "desktop_environment": self.get_desktop_environment(),
            "display_server": self.get_display_server()
        }

    def collect_all_resources(self):
        return {
            "hostname": self.get_hostname(),
            "uptime": self.get_uptime(),
            "cpu": self.get_cpu_load(),
            "memory": self.get_memory_load(),
            "disk": self.get_disk_load()
        }
