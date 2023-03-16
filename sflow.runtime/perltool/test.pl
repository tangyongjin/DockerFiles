#!/usr/bin/perl -w
###  ip-2-ip
###

use warnings;
use strict;
use strict 'vars';
use Getopt::Long;
use Data::Dumper;
use DBI;
# use RRDs;
use NetAddr::IP;
use Time::HiRes qw(ualarm gettimeofday tv_interval);
use File::Path qw(make_path);

# use IXPManager::Config;

# my $ixp = new IXPManager::Config;	# (configfile => $configfile);

my $dbh = DBI->connect('dbi:mysql:database=ixp2;host=172.18.0.2','root','cnix@1234',{AutoCommit=>1,RaiseError=>1,PrintError=>0});
# my $dbh = $ixp->{db};

our $onepool_custid;
our $custid_related_tags;

my $pool = pool_init($dbh);
my $taglist=tag_init($dbh);


 print Dumper( $taglist);

 # print Dumper( $pool);


foreach my $ip_range (keys %{$taglist}) {

		 # print Dumper($ip_range);
 }



my $srcip='10.0.0.1';
my $dstip='10.0.0.4';


	my $tag= detect_ip($srcip,$dstip);

sub detect_ip
{
 
  my ($ip_src,$ip_dst) = @_;
  my $tmp_hash;  
  $tmp_hash->{tag}='UNKNOW';
  $tmp_hash->{poolmac}='12345678';
  $tmp_hash->{direction}='-';

  foreach my $ip_range (keys %{$taglist}) {

		my $network  = NetAddr::IP->new($ip_range);
		my $x_ip_src = NetAddr::IP->new($ip_src);
		my $x_p_dst=   NetAddr::IP->new($ip_dst);


		if ($x_ip_src->within($network)) {
			    $tmp_hash=$taglist->{$ip_range};
                $tmp_hash->{direction}='in';
		        return $tmp_hash;
		}

		if ($x_p_dst->within($network)) {

  			    $tmp_hash=$taglist->{$ip_range};
  			    $tmp_hash->{direction}='out';
		        return $tmp_hash;
		}
 }
   return $tmp_hash;
}


sub pool_related_tag
{
	my ($dbh,$pool_custid) = @_;
	my ($sth,$tags);
	my $query = " select tag from a_ip_biz where custid= $pool_custid ";
	($sth = $dbh->prepare($query)) or die "$dbh->errstr\n";
	$sth->execute() or die "$dbh->errstr\n";
	while (my $rec = $sth->fetchrow_hashref) {

             $tags->{ $rec->{tag} }->{in}=0.01;
             $tags->{ $rec->{tag} }->{out}=0.01;
	}
    $sth->finish();
	return $tags;
}




sub pool_init
{
	my ($dbh) = @_;
	my $sth;
	my $sth2;
    my $poolinfo;

	my $query = " select mac,custid from 
				  view_cust_mac
				  where view_cust_mac.custid in (
				  select distinct custid from a_ip_biz ) ";


	($sth = $dbh->prepare($query)) or die "$dbh->errstr\n";
	$sth->execute() or die "$dbh->errstr\n";

	while (my $onepool = $sth->fetchrow_hashref) {
        
        $onepool_custid= $onepool->{custid};
		my $sql = " select mac,custid from view_cust_mac where view_cust_mac.custid <> $onepool->{custid} ";
        ($sth2 = $dbh->prepare($sql)) ;
        $sth2->execute() ;
        while (my $customer = $sth2->fetchrow_hashref){
        	   my $custmac=$customer->{mac};
        	   $custid_related_tags=pool_related_tag($dbh, $onepool_custid);
               $poolinfo->{$onepool->{mac}}->{$custmac} =$custid_related_tags;
        }
        $sth2->finish();
	}
	$sth->finish();
	return $poolinfo;
}


sub tag_init
{
	my ($dbh) = @_;
	my ($sth,$sth2,$taglist);
	my $query = "  select ip, tag,mac from a_ip_biz,view_cust_mac where a_ip_biz.custid=view_cust_mac.custid";
	$sth = $dbh->prepare($query);
	$sth->execute() ;
	while (my $rec = $sth->fetchrow_hashref) {
	     $taglist->{$rec->{ip}}->{tag}=$rec->{tag};
	     $taglist->{$rec->{ip}}->{poolmac}=$rec->{mac};
	         
	}
	return $taglist;
}


# die;
