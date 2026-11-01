/* restart2 <command>: der reboot(Aufruf) mit Grund, den busybox nicht kann.
 *
 * busybox reboot ruft reboot(MAGIC1, MAGIC2, LINUX_REBOOT_CMD_RESTART, NULL):
 * das Kommando (z.B. "bootloader") geht verloren, jeder Versuch war ein
 * Warmboot ohne Grund. Dieses Werkzeug setzt direkt
 * SYS_reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, <command>) - RESTART2.
 * RESTART2-Konstante nach include/uapi/linux/reboot.h und reboot(2):
 * 0xa1b2c3d4. Der alte Wert 0xe1212120 war keine Kommandokonstante;
 * reboot() gab EINVAL zurueck, ein Neustart fand nie statt.
 * Konstanten hartkodiert, weil musl-Kerncontainer kein linux/reboot.h haben.
 *
 * Bauen:  gcc -static -Os -o restart2 restart2.c   (alpine edge, build-base)
 * Prüfen, ob der Grund ankam: ABOOT-Zählung. Nach `fastboot --set-active=a`
 * (retry 3) booten; erscheint das Fastboot-Menue ~15 s nach der Sonde, ehrt
 * der Bootloader den Grund. Erscheint es erst nach drei vollen Zyklen, war
 * es die Retry-Erschoepfung und der Grund lief ins Leere — auf dem
 * Distro-DTB gibt es keinen poweroff-Knoten, der ihn uebergeben koennte.
 */
#include <stdio.h>
#include <unistd.h>
#include <sys/syscall.h>

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: restart2 <command>\n");
        return 2;
    }
    sync();
    long rc = syscall(SYS_reboot, 0xfee1dead, 0x28121969, 0xa1b2c3d4, argv[1]);
    if (rc < 0) {
        perror("reboot RESTART2");
        return 1;
    }
    sleep(10);
    return 0;
}
