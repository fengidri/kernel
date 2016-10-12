/**
 *   author       :   丁雪峰
 *   time         :   2016-10-11 08:03:36
 *   email        :   fengidri@yeah.net
 *   version      :   1.0.1
 *   description  :
 */

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/kallsyms.h>

struct kprobe kp;

static int hander_pre(struct kprobe *p, struct pt_regs *regs)
{
	printk("Hit it\n");
	return 0;
}

static void hander_post(struct kprobe *p, struct pt_regs *regs,
			unsigned long flags)
{
    dump_stack();
}

static int __init kprobe_init(void)
{
	int ret;
    const char *fun_name = "sdev_show_timeout";
	kp.pre_handler = hander_pre;
	kp.post_handler = hander_post;

	kp.addr = (kprobe_opcode_t *) (kprobe_opcode_t *) kallsyms_lookup_name(fun_name);
	/*
	 * old kernel not have kallsyms_lookup_name(), then we have to manually get the addr
	 * by `cat /proc/kallsyms | awk '/ip_rcv$/ {print $1}'`, finally don't forget add "0x"
	 * eg : kp.addr = 0xffffffff81493ce0;
	 */
	if (kp.addr == NULL) {
		printk(KERN_INFO "kallsyms_lookup_name to %s fail\n", fun_name);
		return 1;
	}

	ret = register_kprobe(&kp);
	if (ret < 0) {
		printk(KERN_INFO "register_kprobe failed, returned %d\n", ret);
		return ret;
	}
	printk(KERN_INFO "Planted kprobe at %p\n", kp.addr);
	return 0;
}

static void __exit kprobe_exit(void)
{
	unregister_kprobe(&kp);
	printk(KERN_INFO "kprobe at %p unregistered\n", kp.addr);
}

module_init(kprobe_init);
module_exit(kprobe_exit);
MODULE_LICENSE("GPL");
