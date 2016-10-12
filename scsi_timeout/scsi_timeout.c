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
#include <linux/proc_fs.h>
#include <linux/seq_file.h>

#define PROC_NAME "scsi_timeout"
#define TIMOUT_DEFAULT 30*1000

extern struct bus_type scsi_bus_type;


static int always_match(struct device *dev, void *data)
{
    return 1;
}


static int scsi_timeout_set(int timeout)
{
    struct device *dev = NULL;
    struct device *pre_dev = NULL;
    struct scsi_device *sdev;


    while ((dev = bus_find_device(&scsi_bus_type, pre_dev, NULL, always_match)))
    {
        if (!scsi_is_sdev_device(dev))
            goto c;

        sdev = to_scsi_device(dev);

        blk_queue_rq_timeout(sdev->request_queue, timeout * HZ / 1000);

        printk(KERN_INFO "scsi %s id:%d HZ: %d timeout: %d\n",
                dev_name(dev),
                sdev->id,
                HZ,
                sdev->request_queue->rq_timeout);

c:
        put_device(pre_dev);
        pre_dev = dev;
    }
    put_device(pre_dev);

    return 0;
}

static int scsi_timeout_set_by_name(int timeout, const char *buf)
{
    struct device *dev = NULL;
    struct scsi_device *sdev;

    dev = bus_find_device_by_name(&scsi_bus_type, NULL, buf);
    if (dev && scsi_is_sdev_device(dev))
    {
        sdev = to_scsi_device(dev);

        blk_queue_rq_timeout(sdev->request_queue, timeout * HZ / 1000);

        printk(KERN_INFO "scsi init_name:%s id:%d HZ: %d timeout: %d\n",
                dev->init_name,
                sdev->id,
                HZ,
                sdev->request_queue->rq_timeout);

        put_device(dev);
    }
    else{
        printk(KERN_INFO "scsi timeout: not found the dev named: %s\n", buf);
    }

    return 0;
}

static int scsi_timeout_proc_show(struct seq_file *m, void *v)
{
    struct device *dev = NULL;
    struct device *pre_dev = NULL;
    struct scsi_device *sdev;


    while ((dev = bus_find_device(&scsi_bus_type, pre_dev, NULL, always_match)))
    {
        if (!scsi_is_sdev_device(dev))
            goto c;

        sdev = to_scsi_device(dev);

        seq_printf(m, "%s id:%d timeout: %dms\n",
                dev_name(dev),
                sdev->id,
                sdev->request_queue->rq_timeout * 1000 / HZ);

c:
        put_device(pre_dev);
        pre_dev = dev;
    }
    put_device(pre_dev);

    return 0;
}

static int scsi_timeout_proc_open(struct inode *inode, struct file *file)
{
    return single_open(file, scsi_timeout_proc_show, NULL);
}

static ssize_t scsi_timeout_proc_write(struct file *file,
        const char __user *buf, size_t length, loff_t *pos)
{
    char buffer[100];
    int c, timeout, err;

    if (!buf || length > sizeof(buffer))
        return -EINVAL;

    err = -EFAULT;
    if (copy_from_user(buffer, buf, length))
        return err;

    err = -EINVAL;
    if (length < sizeof(buffer))
        buffer[length] = '\0';
    else
        buffer[sizeof(buffer) - 1] = '\0';

    c = 0;
    while (c <  length)
    {
        if (buffer[c] == ' ') break;
        ++c;
    }
    if (c >= length) return err;

    buffer[c] = 0;
    ++c;

    while (c <  length)
    {
        if (buffer[c] != ' ') break;
        ++c;
    }
    if (c >= length) return err;

    if (1 != sscanf(buffer + c, "%d\n", &timeout)) return err;
    scsi_timeout_set_by_name(timeout, buffer);

    return length;
}


static struct file_operations scsi_timeout_fops = {
    .owner	= THIS_MODULE,
    .open	= scsi_timeout_proc_open,
    .release = single_release,
    .read	= seq_read,
    .llseek	= seq_lseek,
    .write 	= scsi_timeout_proc_write,
};

static int __init scsi_timeout_init(void)
{
    struct proc_dir_entry *file;

    printk(KERN_INFO "insmod scsi timeout\n");

    file = proc_create(PROC_NAME, 0644, NULL, &scsi_timeout_fops);
    if (!file)
        return -ENOMEM;

    return 0;
}

static void __exit scsi_timeout_exit(void)
{
    remove_proc_entry(PROC_NAME, NULL);
    scsi_timeout_set(TIMOUT_DEFAULT);

    printk(KERN_INFO "rmmod scsi timeout\n");
}

module_init(scsi_timeout_init);
module_exit(scsi_timeout_exit);
MODULE_LICENSE("GPL");
