from __future__ import annotations
import threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from cull_core import find_exact_duplicates, find_near_name_groups, reclaimable_bytes, quarantine

BG='#0d0f0c'; PANEL='#141811'; TEXT='#eef1e8'; MUTED='#99a18f'; ACCENT='#b7e36c'; DANGER='#ff8068'; GOLD='#d7ae58'

def fmt_bytes(n):
    n=float(n)
    for u in ['B','KB','MB','GB','TB']:
        if n<1024 or u=='TB': return f'{n:.1f} {u}'
        n/=1024

class CullApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Cull — Duplicate File Review'); self.geometry('1200x780'); self.minsize(920,620); self.configure(bg=BG)
        self.groups=[]; self.root_var=tk.StringVar(); self.min_var=tk.StringVar(value='1'); self._style(); self._build()
    def _style(self):
        s=ttk.Style(self); s.theme_use('clam'); s.configure('.',background=BG,foreground=TEXT,fieldbackground=PANEL)
        s.configure('TButton',background='#202719',foreground=TEXT,padding=8); s.map('TButton',background=[('active','#2d3721')])
        s.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=28); s.configure('Treeview.Heading',background='#1c2218',foreground=TEXT)
    def _build(self):
        h=tk.Frame(self,bg=BG); h.pack(fill='x',padx=24,pady=(18,10)); tk.Label(h,text='CULL',bg=BG,fg=TEXT,font=('Segoe UI Semibold',28)).pack(side='left'); tk.Label(h,text='  reclaim space without deleting blindly',bg=BG,fg=MUTED).pack(side='left',pady=(12,0))
        row=tk.Frame(self,bg=BG); row.pack(fill='x',padx=24,pady=8); ttk.Entry(row,textvariable=self.root_var).pack(side='left',fill='x',expand=True); ttk.Button(row,text='Browse',command=self.browse).pack(side='left',padx=8); ttk.Button(row,text='Scan',command=self.scan).pack(side='left')
        self.status=tk.Label(self,bg=BG,fg=MUTED,anchor='w'); self.status.pack(fill='x',padx=24,pady=(2,8))
        pan=ttk.Panedwindow(self,orient='horizontal'); pan.pack(fill='both',expand=True,padx=24,pady=(0,18))
        left=tk.Frame(pan,bg=PANEL); right=tk.Frame(pan,bg=PANEL); pan.add(left,weight=2); pan.add(right,weight=3)
        self.group_tree=ttk.Treeview(left,columns=('count','size','waste'),show='headings');
        for c,t,w in [('count','FILES',70),('size','EACH',100),('waste','RECLAIMABLE',120)]: self.group_tree.heading(c,text=t); self.group_tree.column(c,width=w)
        self.group_tree.pack(fill='both',expand=True); self.group_tree.bind('<<TreeviewSelect>>',self.select_group)
        self.file_tree=ttk.Treeview(right,columns=('path','keep'),show='headings',selectmode='extended'); self.file_tree.heading('path',text='PATH'); self.file_tree.heading('keep',text='ACTION'); self.file_tree.column('path',width=560); self.file_tree.column('keep',width=100); self.file_tree.pack(fill='both',expand=True)
        foot=tk.Frame(self,bg=BG); foot.pack(fill='x',padx=24,pady=(0,20)); ttk.Button(foot,text='Quarantine selected',command=self.quarantine_selected).pack(side='right'); ttk.Button(foot,text='Near-name review',command=self.show_near).pack(side='right',padx=8); tk.Label(foot,text='Cull moves files to .cull-quarantine with a manifest; it never permanently deletes them.',bg=BG,fg=GOLD).pack(side='left')
    def browse(self):
        p=filedialog.askdirectory();
        if p:self.root_var.set(p)
    def scan(self):
        root=self.root_var.get();
        if not Path(root).is_dir(): messagebox.showerror('Cull','Choose a folder.'); return
        self.status.config(text='Scanning sizes and hashing candidate duplicates…'); threading.Thread(target=self._scan,args=(root,),daemon=True).start()
    def _scan(self,root):
        try: groups=find_exact_duplicates(root)
        except Exception as e: self.after(0,lambda:messagebox.showerror('Cull',str(e))); return
        self.after(0,lambda:self._show(groups))
    def _show(self,groups):
        self.groups=groups; self.group_tree.delete(*self.group_tree.get_children()); self.file_tree.delete(*self.file_tree.get_children())
        for i,g in enumerate(groups): self.group_tree.insert('', 'end', iid=str(i), values=(len(g.files),fmt_bytes(g.size),fmt_bytes(g.size*(len(g.files)-1))))
        self.status.config(text=f'{len(groups)} exact duplicate groups · {fmt_bytes(reclaimable_bytes(groups))} potentially reclaimable')
    def select_group(self,_=None):
        s=self.group_tree.selection();
        if not s:return
        g=self.groups[int(s[0])]; self.file_tree.delete(*self.file_tree.get_children())
        for i,f in enumerate(g.files): self.file_tree.insert('', 'end', iid=str(i), values=(f.path,'KEEP' if i==0 else 'REVIEW'))
    def quarantine_selected(self):
        s=self.group_tree.selection(); files=self.file_tree.selection()
        if not s or not files: messagebox.showinfo('Cull','Select duplicate files to quarantine.'); return
        g=self.groups[int(s[0])]; paths=[g.files[int(i)].path for i in files]
        if not messagebox.askyesno('Cull',f'Move {len(paths)} file(s) into a reversible quarantine folder?'): return
        try: batch=quarantine(self.root_var.get(),paths)
        except Exception as e: messagebox.showerror('Cull',str(e)); return
        messagebox.showinfo('Cull',f'Moved to:\n{batch}\n\nA manifest was written for recovery.'); self.scan()
    def show_near(self):
        root=self.root_var.get();
        if not Path(root).is_dir(): return
        groups=find_near_name_groups(root); top='\n\n'.join(f'{g.key}:\n  ' + '\n  '.join(g.files[:5]) for g in groups[:10]) or 'No name-based candidates.'
        messagebox.showinfo('Near-name candidates',top)
if __name__=='__main__': CullApp().mainloop()