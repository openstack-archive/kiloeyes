service_id=`keystone service-create --name=monitoring --type=monitoring --description="Kiloeyes monitoring service" | awk 'BEGIN {FS="|"} NR == 6 {print $(NF-1)}'`
service_id=`echo ${service_id}`
echo $service_id
keystone endpoint-create --region RegionOne --service-id=$service_id --publicurl=http://192.168.1.190:9090/v2.0 --internalurl=http://192.168.1.190:9090/v2.0 --adminurl=http://192.168.1.190/v2.0


