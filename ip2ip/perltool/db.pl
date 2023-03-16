#!/usr/bin/perl

use DBI;

my $dbh = DBI->connect('dbi:mysql:database=ixp2;host=172.18.0.2','root','cnix@1234',{AutoCommit=>1,RaiseError=>1,PrintError=>0});
print "2+2=",$dbh->selectrow_array("SELECT * from user"),"\n";

