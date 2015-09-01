# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from subiquity.controller import ControllerPolicy
from subiquity.models import FilesystemModel
from subiquity.ui.views import (DiskPartitionView, AddPartitionView,
                                FilesystemView)
from subiquity.ui.dummy import DummyView
from subiquity.curtin import (curtin_write_storage_actions,
                              curtin_write_postinst_config)


log = logging.getLogger("subiquity.controller.filesystem")

BIOS_GRUB_SIZE_BYTES = 2 * 1024 * 1024   # 2MiB


class FilesystemController(ControllerPolicy):
    def __init__(self, common):
        super().__init__(common)
        self.model = FilesystemModel(self.prober)

    def filesystem(self, reset=False):
        # FIXME: Is this the best way to zero out this list for a reset?
        if reset:
            log.info("Resetting Filesystem model")
            self.model.reset()

        title = "Filesystem setup"
        footer = ("Select available disks to format and mount")
        self.ui.set_header(title)
        self.ui.set_footer(footer, 30)
        self.ui.set_body(FilesystemView(self.model,
                                        self.signal))

    def filesystem_handler(self, reset=False, actions=None):
        if actions is None and reset is False:
            self.signal.emit_signal('network:show')

        log.info("Rendering curtin config from user choices")
        curtin_write_storage_actions(actions=actions)
        log.info("Generating post-install config")
        curtin_write_postinst_config()
        self.signal.emit_signal('installprogress:do-initial-install')
        self.signal.emit_signal('identity:show')

    # Filesystem/Disk partition -----------------------------------------------
    def disk_partition(self, disk):
        log.debug("In disk partition view, using {} as the disk.".format(disk))
        title = ("Partition, format, and mount {}".format(disk))
        footer = ("Partition the disk, or format the entire device "
                  "without partitions.")
        self.ui.set_header(title)
        self.ui.set_footer(footer)
        dp_view = DiskPartitionView(self.model,
                                    self.signal,
                                    disk)

        self.ui.set_body(dp_view)

    def disk_partition_handler(self, spec=None):
        log.debug("Disk partition: {}".format(spec))
        if spec is None:
            self.signal.emit_signal('filesystem:show', [])
        self.signal.emit_signal('filesystem:show-disk-partition', [])

    def add_disk_partition(self, disk):
        log.debug("Adding partition to {}".format(disk))
        footer = ("Select whole disk, or partition, to format and mount.")
        self.ui.set_footer(footer)
        adp_view = AddPartitionView(self.model,
                                    self.signal,
                                    disk)
        self.ui.set_body(adp_view)

    def add_disk_partition_handler(self, disk, spec):
        current_disk = self.model.get_disk(disk)
        log.debug('spec: {}'.format(spec))
        log.debug('disk.freespace: {}'.format(current_disk.freespace))

        try:
            ''' create a gpt boot partition if one doesn't exist '''
            if current_disk.parttype == 'gpt' and \
               len(current_disk.disk.partitions) == 0:
                log.debug('Adding grub_bios gpt partition first')
                size_added = \
                    current_disk.add_partition(partnum=1,
                                               size=BIOS_GRUB_SIZE_BYTES,
                                               fstype=None,
                                               flag='bios_grub')

                # adjust downward the partition size to accommodate
                # the offset and bios/grub partition
                log.debug("Adjusting request down:" +
                          "{} - {} = {}".format(spec['bytes'], size_added,
                                                spec['bytes'] - size_added))
                spec['bytes'] -= size_added
                spec['partnum'] = 2

            if spec["fstype"] in ["swap"]:
                current_disk.add_partition(partnum=spec["partnum"],
                                           size=spec["bytes"],
                                           fstype=spec["fstype"])
            else:
                current_disk.add_partition(partnum=spec["partnum"],
                                           size=spec["bytes"],
                                           fstype=spec["fstype"],
                                           mountpoint=spec["mountpoint"])
        except Exception:
            log.exception('Failed to add disk partition')
            log.debug('Returning to add-disk-partition')
            # FIXME: on failure, we should repopulate input values
            self.signal.emit_signal('filesystem:add-disk-partition', disk)

        log.info("Successfully added partition")

        log.debug("FS Table: {}".format(current_disk.get_fs_table()))
        self.signal.emit_signal('filesystem:show-disk-partition', disk)

    def connect_iscsi_disk(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))

    def connect_ceph_disk(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))

    def create_volume_group(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))

    def create_raid(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))

    def setup_bcache(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))

    def add_first_gpt_partition(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))

    def create_swap_entire_device(self, *args, **kwargs):
        self.ui.set_body(DummyView(self.signal))
