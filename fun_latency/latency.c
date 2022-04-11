#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/device.h>
#include <linux/proc_fs.h>
#include <linux/delay.h>
#include <linux/seq_file.h>

static u64 fun_start, fun_count, fun_total;

static int time = 1;
module_param(time, int, 0644);

static char *fun_name = "__alloc_skb";
module_param(fun_name, charp, 0644);

static int handler_fun_start(struct kprobe *p, struct pt_regs *regs)
{
	fun_start = rdtsc();
	return 0;
}

static int handler_fun_end(struct kretprobe_instance *p, struct pt_regs *regs)
{
	fun_total += rdtsc() - fun_start;
	fun_count += 1;
	return 0;
}

static struct kprobe kp = { };
static struct kretprobe krp = { };

static int start_probe(const char *fun_name)
{
	int ret;

	memset(&kp, 0, sizeof(kp));
	memset(&krp, 0, sizeof(krp));

	kp.pre_handler = handler_fun_start;
	kp.symbol_name = fun_name;
	ret = register_kprobe(&kp);
	if (ret < 0) {
		printk(KERN_INFO "register_kprobe failed, returned %d %s\n", ret, fun_name);
		return ret;
	}

	krp.handler = handler_fun_end;
	krp.kp.symbol_name = fun_name;
	ret = register_kretprobe(&krp);
	if (ret < 0) {
		unregister_kprobe(&kp);
		printk(KERN_INFO "register_kretprobe failed, returned %d\n", ret);
		return ret;
	}
	return 0;
}

static void stop_probe(void)
{
	unregister_kprobe(&kp);
	unregister_kretprobe(&krp);
}

static int fun_latency(struct seq_file *m, void *v)
{
	char buf[1024];
	int ret, l;
	u64 latency = 0;

	fun_start = 0;
	fun_count = 0;
	fun_total = 0;

	ret = start_probe(fun_name);
	if (ret)
		return ret;

	msleep(time * 1000);

	stop_probe();

	if (fun_count)
		latency = fun_total / fun_count;

	l = sprintf(buf, "%s latency: %llu count: %llu\n", fun_name, latency, fun_count);

	seq_write(m, buf, l);

	return 0;
}

static struct proc_dir_entry *proc;

static int __init kprobe_init(void)
{
	proc = proc_create_single("fun_latency", 0, NULL, fun_latency);
	if (!proc){
		printk(KERN_INFO "create proc failed\n");
		return -1;
	}

	return 0;
}

static void __exit kprobe_exit(void)
{
	proc_remove(proc);
}

module_init(kprobe_init)
module_exit(kprobe_exit)
MODULE_LICENSE("GPL");

