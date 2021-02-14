<?php
// Zabbix GUI configuration file
global $DB;

$DB['TYPE']     = 'MYSQL';
$DB['SERVER']   = '172.18.0.2';
$DB['PORT']     = '3306';
$DB['DATABASE'] = 'zabbix';
$DB['USER']     = 'root';
$DB['PASSWORD'] = 'cnix@1234';

// SCHEMA is relevant only for IBM_DB2 database
$DB['SCHEMA'] = '';

$ZBX_SERVER      = 'ZW_ZBX_SERVER';
$ZBX_SERVER_PORT = 'ZW_ZBX_SERVER_PORT';
$ZBX_SERVER_NAME = 'ZW_ZBX_SERVER_NAME';

$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;
?>
