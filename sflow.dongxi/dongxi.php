<?php

/*
for docker and  host
阿里巴巴 custid :11
virtualinterfaceID 12,52
vlaninterface :9,49
mac f44c7f938277 ,f44c7f99abe9


世纪互联-1  dc38e11388a6


爱奇艺CDN2  58696c9db3d8

*/

function debug($arr)
{
    print_r($arr);
}



class Sflow
{
    const INTERVAL = 60;
    
    private $startpoint = null;
    public  $mac_cust = array();
    public  $type_cust = array();
    public  $matrix = array();
    public  $cust_virtualinterfaceid_vlaninterfaceid=array();
    
    
    
    public $servername = null;

    public $username = "root";
    public $password = "cnix@1234";
    public $dbname = "ixp2";
    
    public  $dbconn;
    private $basedir = '/ixpdata/rrd';
   
    
    public function __construct() {

        $this->startpoint=time();


        $dbserver = getenv('dbserver', true) ?: getenv('dbserver');
        
        if($dbserver){
            $this->servername =$dbserver;
        }
         else
        {
            die ("Environment var  dbserver not set. \n" );
        }

        @$this->dbconn = mysqli_connect($this->servername, $this->username, $this->password, $this->dbname);
        $this->type_cust = $this->init_type_cust();
        $this->mac_cust  = $this->init_mac_cust();
        $this->matrix    = $this->init_matrix();
        $this->cust_virtualinterfaceid_vlaninterfaceid=$this->init_cust_vv();
    
        $this->debug_cfg();
    } 
    

 
    public function debug_cfg(){
          
          // debug($this->type_cust);  
          // debug($this->mac_cust); die ;
          // debug($this->matrix['dongxi']); die; 
          // debug($this->matrix['dxtotal']); die; 
          // debug($this->cust_virtualinterfaceid_vlaninterfaceid);die;
    }



    public function dry_run(){

          echo 'dry_run';


          $this->summaryMatrix();
          
          // debug($this->type_cust);  
          // debug($this->mac_cust); die ;
          // debug($this->matrix['dongxi']); die; 
          // debug($this->matrix['dxtotal']); die; 
          // debug($this->cust_virtualinterfaceid_vlaninterfaceid);die;
    }


     public function init_matrix() {
        
        $sql      = "select  id as onetype_id from a_biz_type";
        $result   = $this->dbconn->query($sql);
        $biztypes = array();
        while ($row = $result->fetch_assoc()) {
            $tmp                          = array(
                'in' => 0,
                'out' => 0
            );
            $biztypes[$row['onetype_id']] = $tmp;
        }
        
        $rrdtypes = array(
            'bytes' => $biztypes,
            'pkts' => $biztypes
        );
        
        
        $sql    = "select  id as cust_id  from  cust ";
        $result = $this->dbconn->query($sql);
        
        
        $matrix = array();
        $dongxi = array();
        
        while ($row = $result->fetch_assoc()) {
            $dongxi[$row['cust_id']] = $rrdtypes;
        }
        
        $matrix['dongxi'] = $dongxi;
        $dxtotal = array();
        foreach (array_keys($biztypes) as $one_biztype) {
            $dxtotal[$one_biztype] = array(
                'bytes' => $biztypes,
                'pkts' => $biztypes
            );
        }
        
        $matrix['dxtotal'] = $dxtotal;
        return $matrix;
    }
    
    
    public function init_mac_cust(){
        
        $sql      = "select mac,custid from view_cust_mac";
        $result   = $this->dbconn->query($sql);
        $mac_cust = array();
        
        while ($row = $result->fetch_assoc()) {
            $mac_cust[$row['mac']] = array(
                'custid' => $row['custid']
            );
        }
        
        return $mac_cust;
        
    }
    
    public function init_type_cust(){
        
        
        $sql       = "select biz_id, customer_id from cust_biz";
        $result    = $this->dbconn->query($sql);
        $type_cust = array();
        
        while ($row = $result->fetch_assoc()) {
            $type_cust[$row['customer_id']] = array(
                'biz_id' => $row['biz_id']
            );
        }
        return $type_cust;
    }

    public function init_cust_vv(){
        $sql= "select  custid,virtualinterfaceid,vlaninterfaceid from view_vlaninterface_details_by_custid order by custid ,vlaninterfaceid";
        $result    = $this->dbconn->query($sql);
        $cust_virtualinterfaceid_vlaninterfaceid=array();
        while ($row = $result->fetch_assoc()) {
            $cust_virtualinterfaceid_vlaninterfaceid[] = $row;
        }
        return $cust_virtualinterfaceid_vlaninterfaceid;
    }

    public function find_cust_by_mac($mac){
        
        $custid = null;
        if (array_key_exists($mac, $this->mac_cust)) {
            
            $custid = $this->mac_cust[$mac]['custid'];
        }
        return $custid;
    }
    
    public function find_type_by_cust($custid){
        
        $custtype = 1000;  // 1000为未知类型

        if (array_key_exists($custid, $this->type_cust)) {
            
            $custtype = $this->type_cust[$custid]['biz_id'];
        }
        
        return $custtype;
    }

    public function find_vlanid_by_cust($custid){
        $vli=null;
        foreach ($this->cust_virtualinterfaceid_vlaninterfaceid as   $one_cust_vv) {
                  
                  if($one_cust_vv['custid']==$custid){
                    $vli=$one_cust_vv['vlaninterfaceid'];
                    return $vli;
                  }     
         } 
        return $vli;
    }
    
    
    private function parseFlow($cdr){
        $keys = array(
            'flowtype',
            'device',
            'input_port',
            'output_port',
            'src_mac',
            'dst_mac',
            'ethernet_type',
            'in_vlan',
            'out_vlan',
            'src_ip',
            'dst_ip',
            'ip_protocol',
            'ip_tos',
            'ip_ttl',
            'src_port_or_icmp_type',
            'dst_port_or_icmp_code',
            'tcp_flags',
            'packet_size',
            'ip_size',
            'sampling_rate'
        );
        $data = array_combine($keys, $cdr);
        return $data;
    }
    
    
    private function updateMatrix($slowcdr){
        $cdr = $this->parseFlow($slowcdr);
        $samplerate = $cdr['sampling_rate'];
        $pktsize    = $cdr['packet_size'];
        
        $flowtype = $cdr['flowtype'];

        $src_mac  = $cdr['src_mac'];
        $dst_mac  = $cdr['dst_mac'];

        $src_cust = $this->find_cust_by_mac($src_mac);
        $dst_cust = $this->find_cust_by_mac($dst_mac);
        $src_type = $this->find_type_by_cust($src_cust);
        $dst_type = $this->find_type_by_cust($dst_cust);
        
        $custid_exists_in_matrix=false;

        if( array_key_exists($src_cust, $this->matrix['dongxi']) &&  array_key_exists($dst_cust, $this->matrix['dongxi'])  ){
            $custid_exists_in_matrix=true;
        }

        if ( $custid_exists_in_matrix &&intval($src_cust)>0 && intval($dst_type)>0 && intval($dst_cust)>0 && intval($src_type)>0 && $flowtype == 'FLOW') {
         
            $this->matrix['dongxi'][$src_cust]['bytes'][$dst_type]['in'] += $pktsize * $samplerate;
            $this->matrix['dongxi'][$dst_cust]['bytes'][$src_type]['out'] += $pktsize * $samplerate;
            $this->matrix['dongxi'][$src_cust]['pkts'][$dst_type]['in'] += $samplerate;
            $this->matrix['dongxi'][$dst_cust]['pkts'][$src_type]['out'] += $samplerate;
          
            $this->matrix['dxtotal'][$src_type]['bytes'][$dst_type]['in'] += $pktsize * $samplerate;
            $this->matrix['dxtotal'][$dst_type]['bytes'][$src_type]['out'] += $pktsize * $samplerate;
            
            $this->matrix['dxtotal'][$src_type]['pkts'][$dst_type]['in'] += $samplerate;
            $this->matrix['dxtotal'][$dst_type]['pkts'][$src_type]['out'] += $samplerate;
        }
        
    }

    private function summaryMatrix(){
        
        //审计
        $T_biz_in=0;
        $T_biz_out=0;
        $T_total_in=0;
        $T_total_out=0;
    
         // 客户-东西向    
         foreach(array_keys($this->matrix['dongxi']) as $one_custid) {
               $srcvli=$this->find_vlanid_by_cust($one_custid);
               foreach (  array('bytes','pkts')  as $rrdtype) {
                     foreach ( array_keys($this->matrix['dongxi'][$one_custid][$rrdtype]) as  $one_biz) {
                          $file_tpl="$this->basedir/ipv4/".$rrdtype."/dongxi/"."src-%05d/dongxi.ipv4.$rrdtype.src-%05d.biz-%05d.rrd";
                          $rrdfile = sprintf( $file_tpl, $srcvli, $srcvli, $one_biz);
                          $biz_in  = $this->matrix['dongxi'][$one_custid][$rrdtype][$one_biz]['in'];
                          $biz_out = $this->matrix['dongxi'][$one_custid][$rrdtype][$one_biz]['out'];
                          
                          if($rrdtype=='bytes'){
                             $T_biz_in+= $biz_in ;
                             $T_biz_out+= $biz_out ;
                          }
                          

                          echo $rrdfile; 
                          $this->build_update_rrd ($rrdtype,$rrdfile,  $biz_in, $biz_out );
                          
                     }
               }
         }


         // 东西向汇总
         foreach(array_keys($this->matrix['dxtotal']) as $type_a) {
              foreach (array('bytes','pkts')  as $rrdtype){
                  foreach (   array_keys($this->matrix['dxtotal'][$type_a][$rrdtype])  as $type_b){
                          $file_tpl = "$this->basedir/ipv4/".$rrdtype."/dxtotal/"."biz-%05d/dongxi.ipv4.$rrdtype.biz-%05d.biz-%05d.rrd";
                          $rrdfile = sprintf( $file_tpl,$type_a, $type_a, $type_b);
                        
                          $total_in  = $this->matrix['dxtotal'][$type_a][$rrdtype][$type_b]['in'];
                          $total_out = $this->matrix['dxtotal'][$type_a][$rrdtype][$type_b]['out'];
                          
                       
                           if($rrdtype=='bytes'){
                                $T_total_in+= $total_in;
                                $T_total_out+=$total_out;
                          }

                          $this->build_update_rrd ($rrdtype,$rrdfile,  $total_in, $total_out );
                  }
              }
        }

        $audit=array(

            'T_biz_in'=>$T_biz_in,
            'T_biz_out'=>$T_biz_out,
            'T_total_in'=>$T_total_in,
            'T_total_out'=>$T_total_out
        );

        // debug($audit);
    }
    

    public function build_update_rrd($rrdtype,$rrdfile,$biz_in,$biz_out){

            if (!file_exists($rrdfile)) {

                $path= dirname($rrdfile);
                if (!file_exists($path)) {
                    mkdir($path, 0777, true);
                }

        // 创建rrd文件


        //          $opts = array( "--step", "300", "--start", 0,
        //    "DS:input:COUNTER:600:U:U",
        //    "DS:output:COUNTER:600:U:U",
        //    "RRA:AVERAGE:0.5:1:600",
        //    "RRA:AVERAGE:0.5:6:700",
        //    "RRA:AVERAGE:0.5:24:775",
        //    "RRA:AVERAGE:0.5:288:797",
        //    "RRA:MAX:0.5:1:600",
        //    "RRA:MAX:0.5:6:700",
        //    "RRA:MAX:0.5:24:775",
        //    "RRA:MAX:0.5:288:797"
        // );

                $rrds_create_options = array("--step", "300", "--start", 0,
                  'DS:traffic_in:GAUGE:600:U:U',
                  'DS:traffic_out:GAUGE:600:U:U',
                  'RRA:AVERAGE:0.5:1:600',    'RRA:MAX:0.5:1:600',
                  'RRA:AVERAGE:0.5:6:700',    'RRA:MAX:0.5:6:700', 
                  'RRA:AVERAGE:0.5:24:750',   'RRA:MAX:0.5:24:750',  
                  'RRA:AVERAGE:0.5:288:3650', 'RRA:MAX:0.5:288:3650',
                );

                // 版本变化:rrd_create 只接受两个参数.
                // $ret = rrd_create($rrdfile, $rrds_create_options, count($rrds_create_options));
                $ret = rrd_create($rrdfile, $rrds_create_options);
            
            } 

            // $now = time();
           
            $rrdvalues = "N:".intval($biz_in/self::INTERVAL).":".intval($biz_out/self::INTERVAL);
         
            if ($rrdtype=='bytes') {
                        echo $rrdfile.'-->'.$rrdvalues."\n";
            }
     
            $ret = rrd_update($rrdfile, array($rrdvalues));
            if (! $ret) {
             echo "rrd_update error:".rrd_error()."\n";
            }
    }
   
    
    public function readInput()
    {
        while ($csv = fgetcsv(STDIN)) {
            $now = time();
            if ($now - $this->startpoint >= self::INTERVAL) {
                
                echo "INTERVAL_get\n";

                $this->summaryMatrix();


                $this->type_cust = $this->init_type_cust();
                $this->mac_cust  = $this->init_mac_cust();
                $this->matrix    = $this->init_matrix();
                $this->startpoint = time();
            }
            
            $this->updateMatrix($csv);
        }
    }
}


echo "开始 \n ";

$sflow = new Sflow;

// $sflow->dry_run();
// die;

$sflow->readInput();
exit;
