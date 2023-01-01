# Easy Dualboot Computer Manage

# Configure Linux-running computer to be managed by Home Assistant.
Create a user named 'homeassistant' on your Linux-running computer and give it a strong password
```useradd -m -p $(openssl passwd -1 "your_password") homeassistant``` and add the following to the sudoers file using visudo:

```# Allow homeassistant user to execute shutdown, init, systemctl, pm-suspend, awk, grub-reboot, and grub2-reboot without a password
homeassistant ALL=(ALL) NOPASSWD: /sbin/shutdown
homeassistant ALL=(ALL) NOPASSWD: /sbin/init
homeassistant ALL=(ALL) NOPASSWD: /usr/bin/systemctl
homeassistant ALL=(ALL) NOPASSWD: /usr/sbin/pm-suspend
homeassistant ALL=(ALL) NOPASSWD: /usr/bin/awk
homeassistant ALL=(ALL) NOPASSWD: /usr/sbin/grub-reboot
homeassistant ALL=(ALL) NOPASSWD: /usr/sbin/grub2-reboot
```

