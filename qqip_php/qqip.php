 <?php


function array_to_string($arr, $key=null)
{
    $str = '';
    foreach ($arr as $one_item) {
        $str .= $one_item . ',';
    }

    $str = rtrim($str, ",");
    if (strlen($str) == 0) {
        $str = '-1';
    }
    return $str;
}


$servername = "114.113.88.2";
$username = "root";
$password = "cnix@1234";
$dbname = "ixp2";
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
} 
 


//取昨天的日期

  $sql = " select atime from qq_iplist_detail where id in (select max(id) as id from qq_iplist_detail)";
  $previous_date=1;
  $result = $conn->query($sql);
  if ($result->num_rows > 0) {
      while($row = $result->fetch_assoc()) {
           $previous_date= $row['atime'];
      }
  }  


//取昨天的所有域名和ip ,得到 yesterday_domain
  $sql=" select  domain,ip   from  qq_iplist_detail where atime='{$previous_date}' ";
  $result = $conn->query($sql);
  $yesterday_domain=array();
  if ($result->num_rows > 0) {
      while($row = $result->fetch_assoc()) {
        $yesterday_domain[ $row['domain']][]=$row['ip'];
      }
  }





 
 
//取今天运行的域名,从腾讯读取,得到  today_domain
$ch = curl_init();
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$xdate= date("Y0md", time()- 60 * 60 * 24);
$url="http://play.domain.qq.com/getdomain.php?dtime=".$xdate;
curl_setopt($ch, CURLOPT_URL,$url);
$result=curl_exec($ch);
curl_close($ch);
$qq_array= json_decode($result, true);
 
$atime=$qq_array['atime'];
$today_domain=$qq_array['data'];

 


foreach ($qq_array['data'] as $domain => $ip_array  ) {
     $row=array();
     foreach ($ip_array as $key => $ipaddr) {
         $atime=substr($qq_array['atime'],0,8);
         $sql=" insert into qq_iplist_detail(atime,domain,ip) values  ('$atime','$domain','$ipaddr') ";
         $conn->query($sql);
     }
}
 
  


 $today_domain_list=array_keys($today_domain);
 $yesterday_domain_list=array_keys($yesterday_domain);


 $added=array_diff($today_domain_list, $yesterday_domain_list);

 

 

 $L_domain_add_str=  array_to_string ($added,null).'  ';
 
  
 //昨天和今天都存在的公共域名
 $intersect=array_intersect($today_domain_list, $yesterday_domain_list);

 $ips_diff_added=array();
 $ips_diff_deleted=array();

//对每个公共域名检查变动的IP
 foreach ($intersect as $key => $pub_domain) {
      
      $new_ips=$today_domain[$pub_domain];
      $old_ips=$yesterday_domain[$pub_domain];
 
      //新增加的ip
      $ip_diff_add=array_diff( $new_ips,$old_ips);
      if($ip_diff_add){
        $ips_diff_added[$pub_domain]=$ip_diff_add;
      }
 

      //减少的ip
      $ip_diff_deleted=array_diff( $old_ips,$new_ips);
      if($ip_diff_deleted){
        $ips_diff_deleted[$pub_domain]=$ip_diff_deleted;
      }
 
 }


 $L_ip_added='';
 foreach ($ips_diff_added as $key => $value) {
   $L_ip_added.=$key.'=>'.array_to_string($value).' ';
 }

 $L_ip_deleted='';
 foreach ($ips_diff_deleted as $key => $value) {
   $L_ip_deleted.=$key.'=>'.array_to_string($value).' ';
 }

  

$total_change=    $previous_date.'->'.date("Ymd", time()- 60 * 60 * 24).'[New_Domain:'.$L_domain_add_str.'IP_ADDED:['.$L_ip_added.']';

$total_change.=' IP_DEL:['.$L_ip_deleted.']';  

$sql=" insert into qq_iplist_diff(diff) values  ('$total_change') ";
$conn->query($sql);

?>
