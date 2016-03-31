#VBoxManage snapshot h2-compute01 restore "Snapshot 3"
#VBoxManage snapshot h2-nova restore "Snapshot 3"
VBoxManage snapshot h2-controller restore "Snapshot 3"

#vboxmanage startvm h2-compute01 --type headless
#vboxmanage startvm h2-nova --type headless
vboxmanage startvm h2-controller --type headless
