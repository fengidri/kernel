/**
 *   author       :   丁雪峰
 *   time         :   2016-10-12 05:51:48
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kallsyms.h>
#include <linux/blkdev.h>

#include <scsi/scsi.h>
#include <scsi/scsi_device.h>

extern struct bus_type scsi_bus_type;


static int always_match(struct device *dev, void *data)
{
    return 1;
}

static int __init scsi_timeout_init(void)
{
    struct device *dev = NULL;
    struct device *pre_dev = NULL;
    struct scsi_device *sdev;


    while ((dev = bus_find_device(&scsi_bus_type, pre_dev, NULL, always_match)))
    {
        if (!scsi_is_sdev_device(dev))
            goto c;

        sdev = to_scsi_device(dev);

        blk_queue_rq_timeout(sdev->request_queue, 0.1 * HZ);

        printk(KERN_INFO "scsi init_name:%s id:%d HZ: %d timeout: %d\n",
                dev->init_name,
                sdev->id,
                HZ,
                sdev->request_queue->rq_timeout);

c:
        put_device(pre_dev);
        pre_dev = dev;
    }

    return 0;
}

static void __exit scsi_timeout_exit(void)
{
}

module_init(scsi_timeout_init);
module_exit(scsi_timeout_exit);
MODULE_LICENSE("GPL");
