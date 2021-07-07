#include <err.h>
#include <fcntl.h>
#include <libelf.h>
#include <stdio.h>
#include <stdlib.h>
#include <sysexits.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
    int           fd;
    Elf           *e;
    Elf_Scn       *scn;
    Elf_Data      *data;
    Elf64_Ehdr    *ehdr;
    Elf64_Phdr    *phdr;
    Elf64_Shdr    *shdr;
    char *code;
    int code_sz;
    struct stat stat;

    if (argc != 3)
        errx(EX_USAGE,"input... ./%s bpf_code output\n",argv[0]);

    if (elf_version(EV_CURRENT) == EV_NONE)
        errx(EX_SOFTWARE,"elf_version is ev_none, wtf? %s\n",elf_errmsg(-1));

    if ((fd = open(argv[1], O_RDONLY)) < 0)
        errx(EX_OSERR, "open %s\n",elf_errmsg(-1));

    fstat(fd, &stat);
    code_sz = stat.st_size;

    code = malloc(code_sz);

    read(fd, code, code_sz);


    if ((fd = open(argv[2], O_WRONLY | O_CREAT, 0777)) < 0)
        errx(EX_OSERR, "open %s\n",elf_errmsg(-1));

    if ((e = elf_begin(fd, ELF_C_WRITE, NULL)) == NULL)
        errx(EX_SOFTWARE,"elf_begin %s\n",elf_errmsg(-1));

    if ((ehdr = elf64_newehdr(e)) == NULL)
        errx(EX_SOFTWARE,"elf32_newehdr %s\n",elf_errmsg(-1));
    /*
       without these definitions objdump/readelf/strace/elf loader
       will fail to load the binary correctly
       be sure to pick them carefully and correctly, preferred exactly like the
       ones like the system you are running on (so if you are running x86,
       pick the same values you seen on a regular readelf -a /bin/ls
       */
    ehdr->e_ident[EI_DATA] = ELFDATA2LSB;
    ehdr->e_ident[EI_CLASS] = ELFCLASS64;
    ehdr->e_machine = 0xf7;
    //    ehdr->e_type = ET_REL;
    ehdr->e_type = ET_EXEC;
    //    ehdr->e_entry = 0x8040800;
    ehdr->e_entry = 0;

    if ((phdr = elf64_newphdr(e,1)) == NULL)
        errx(EX_SOFTWARE,"elf32_newphdr %s\n",elf_errmsg(-1));

    if ((scn = elf_newscn(e)) == NULL)
        errx(EX_SOFTWARE,"elf32_newscn %s\n",elf_errmsg(-1));

    if ((data = elf_newdata(scn)) == NULL)
        errx(EX_SOFTWARE,"elf32_newdata %s\n",elf_errmsg(-1));

    data->d_align = 8;
    data->d_off = 0LL;
    data->d_buf = code;
    data->d_type = ELF_T_AUXV; // code :x
    data->d_size = code_sz;
    data->d_version = EV_CURRENT;

    if ((shdr = elf64_getshdr(scn)) == NULL)
        errx(EX_SOFTWARE,"elf32_getshdr %s\n",elf_errmsg(-1));

    shdr->sh_name = 0;
    shdr->sh_type = SHT_PROGBITS;
    shdr->sh_flags = SHF_EXECINSTR | SHF_ALLOC;
    shdr->sh_entsize = 0; // only used if we hold a table

    if (elf_update(e, ELF_C_NULL) < 0)
        errx(EX_SOFTWARE,"elf_update_1 %s\n",elf_errmsg(-1));

    phdr->p_type = PT_LOAD;
    phdr->p_offset = ehdr->e_phoff;
    phdr->p_filesz = elf32_fsize(ELF_T_PHDR, 1, EV_CURRENT);
    phdr->p_vaddr = 0x8040800;
    phdr->p_paddr = 0x8040800;
    phdr->p_align = 4;
    phdr->p_filesz = code_sz;
    phdr->p_memsz = code_sz;
    phdr->p_flags = PF_X | PF_R;

    elf_flagphdr(e, ELF_C_SET, ELF_F_DIRTY);

    if (elf_update(e, ELF_C_WRITE) < 0 )
        errx(EX_SOFTWARE,"elf32_update_2 %s\n",elf_errmsg(-1));

    elf_end(e);
    close(fd);
    return 1;
}
