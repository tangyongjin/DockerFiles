#!/usr/bin/perl -w

use warnings;
use strict;
use Getopt::Long;
use Data::Dumper;
use DBI;
use RRDs;
use Time::HiRes qw(ualarm gettimeofday tv_interval);
use File::Path qw(make_path);

use IXPManager::Config;

my $ixp = new IXPManager::Config;	# (configfile => $configfile);



my $dbh = DBI->connect('dbi:mysql:database=ixp2;host=172.18.0.2','root','cnix@1234',{AutoCommit=>1,RaiseError=>1,PrintError=>0});
my $rrdcached = defined($ixp->{ixp}->{sflow_rrdcached}) ? $ixp->{ixp}->{sflow_rrdcached} : 1;




my $basedir ='/ixpdata/rrd/ip2ip';
my $timer_period = 60;
my $daemon = 1;



# GetOptions(
# 	'debug!'		=> \$debug,
# 	'insanedebug!'		=> \$insanedebug,
# 	'daemon!'		=> \$daemon,
# 	'sflowtool=s'		=> \$sflowtool,
# 	'sflowtool_opts=s'	=> \$sflowtool_opts,
# 	'sflow_rrddir=s'	=> \$basedir,
# 	'flushtimer=i'		=> \$timer_period
# );



 
my $matrix = matrix_init($dbh);


my $execute_periodic = 0;
my $quit_after_periodic = 0;



# handle signals gracefully
$SIG{TERM} = sub { $execute_periodic = 1; $quit_after_periodic = 1; };
$SIG{QUIT} = sub { $execute_periodic = 1; $quit_after_periodic = 1; };
$SIG{HUP} = sub { $execute_periodic = 1; };

 
$SIG{ALRM} = sub { $execute_periodic = 1 };
ualarm ( $timer_period*1000000, $timer_period*1000000);

my $tv = [gettimeofday()];



my $sflowtool_opts=" -p 5502 -l ";
my $sflowtool="/usr/local/bin/sflowtool";
my $sflowpid = open (SFLOWTOOL, '-|', $sflowtool, split(' ', $sflowtool_opts));

# methodology is to throw away as much crap as possible before parsing
while (<SFLOWTOOL>) {
	next unless (substr($_, 0, 4) eq 'FLOW');	# don't use regexp here for performance reasons
	my ($ipprotocol);

	chomp;


	
	my @sample = split (/,/);			# don't use regexp here for performance reasons
	my (undef, $agent, $srcswport, $dstswport, $srcmac, $dstmac, $ethertype, $vlan, undef, 
		$srcip, $dstip, $protocol, $tos, $ttl,
		$srcport, $dstport, $tcpflags, $pktsize, $payloadsize, $samplerate) = @sample;

	if ($ethertype eq '0x0800') {
		$ipprotocol = 4;
	} elsif ($ethertype eq '0x86dd') {
		$ipprotocol = 6;
	} else {
		next;
	}

	 


	
	if ($matrix->{ip2ip}->{$srcmac}->{$dstip} ){
      $matrix->{ip2ip}->{$srcmac}->{$dstip}+= $pktsize * $samplerate;
	}
	else
	{
	  $matrix->{ip2ip}->{$srcmac}->{$dstip} = $pktsize * $samplerate;
	}
    
     

	if ($execute_periodic) {
		if ($quit_after_periodic) {
			# sometimes sflowtool doesn't die properly. Need to prioritise kill.
			kill 9, $sflowpid;
		}
		my $newtv = [gettimeofday()];
		my $interval = tv_interval($tv, $newtv);
		$tv = $newtv;
	    process_rrd($interval, $matrix, $rrdcached);
		if ($quit_after_periodic) {
			exit 0;
		}
		$execute_periodic = 0;
		 
		$matrix = matrix_init($dbh);
	}
}

close (SFLOWTOOL);

# try to kill off sflowtool if it's not already dead
kill 9, $sflowpid;

# oops, we should never exit
die "Oops, input pipe died. Aborting.\n";



sub process_rrd {

	my ($interval, $matrix, $rrdcached) = @_;
	my ($aggregate, $rrdfile);
	
    foreach my $srcmac (keys %{$matrix->{ip2ip}}) 
    {
    	   foreach my $ipaddress (keys %{$matrix->{ip2ip}->{$srcmac}}) 
					{
					   print $srcmac."\n";
					   print $ipaddress."\n";
   				   	   $rrdfile = $basedir."/".$srcmac."/".$ipaddress.".rrd";
                       my $traffic= $matrix->{ip2ip}->{$srcmac}->{$ipaddress};
                       build_update_rrd ($rrdfile,$traffic,$interval, $rrdcached);
					}
    
    }
}



sub build_update_rrd
{
	use File::Path qw(make_path);
	use File::Basename;
		
	my ($rrdfile,$traffic, $interval, $rrdcached) = @_;
	my @rrds_options = ();
	my $rrd_err;

	$traffic = 0 if (!defined($traffic));
 
	

	if (!-s $rrdfile) {
		my $dir = dirname($rrdfile);
		if (!-d $dir) {
			make_path($dir) or die "Could not make directory: $dir: $!\n";
		}

		my @rrds_create_options = (
			 
			'DS:traffic_out:GAUGE:600:U:U',
			'RRA:AVERAGE:0.5:1:600',    'RRA:MAX:0.5:1:600',
			'RRA:AVERAGE:0.5:6:700',    'RRA:MAX:0.5:6:700', 
			'RRA:AVERAGE:0.5:24:750',   'RRA:MAX:0.5:24:750',  
			'RRA:AVERAGE:0.5:288:3650', 'RRA:MAX:0.5:288:3650',
		);

		RRDs::create ($rrdfile, @rrds_create_options);
		$rrd_err = RRDs::error;
		print STDERR "WARNING: while updating $rrdfile: $rrd_err\n" if $rrd_err;
	}

	if ($rrdcached) {
		push @rrds_options, '--daemon', 'unix:/var/run/rrdcached.sock';
	}

	my $rrdvalues = "N:".int($traffic/$interval);
	RRDs::update ($rrdfile, @rrds_options, $rrdvalues);

	$rrd_err = RRDs::error;
	print STDERR "WARNING: while updating $rrdfile: $rrd_err\n" if $rrd_err;
}



sub matrix_init
{
	my ($dbh) = @_;
	my ($sth, $matrix);

	# we need this to be distinct because of 802.3ag LAGs, where there
	# can be multiple physical ports associated with a single VLI

	my $query = " select * from  macaddress ";

	($sth = $dbh->prepare($query)) or die "$dbh->errstr\n";
	$sth->execute() or die "$dbh->errstr\n";

	while (my $rec = $sth->fetchrow_hashref) {
	    $matrix->{ip2ip}->{$rec->{mac}} ={};
	}

	foreach my $srcmac (keys %{$matrix->{ip2ip}}) 
    {
        	my $dir=$basedir."/".$srcmac;
			if (!-d $dir) {
						make_path($dir) or die "Could not make directory: $dir: $!\n";
			}
    }
	return $matrix;
}

 