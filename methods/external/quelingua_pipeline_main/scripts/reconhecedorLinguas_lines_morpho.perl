#!/usr/bin/perl

#IDENTIFICA SE UM TEXTO E ESPANHOL OU GALEGO 

#le um ficheiro a identificar (pipe) que foi previamente tokenizado
#le um ficheiro com todos os lexicons disponiveis. O formato é "token ling"

binmode STDIN, ':utf8';
binmode STDOUT, ':utf8';
use utf8;


my $lexicon = shift(@ARGV);
open (L, $lexicon) or die "O ficheiro não pode ser aberto: $!\n";
binmode L, ':utf8';


my $suffix = shift(@ARGV);
open (S, $suffix) or die "O ficheiro não pode ser aberto: $!\n";

my $ling_def_1="gl";
my $ling_def_2="en";

my $Separador = "[\.\,\;\:\«\»\"\&\%\+\=\$\#\(\)\<\>\!\¡\?\¿\\[\\]]" ;

my $i=1;
my $term="";
my $suffix="";
my $ling="";
my %Rank;
my %Lex;
my %Suffix;

while (my $line = <L>) {
   chomp $line;
  ($term, $ling) = split ("\t", $line);

   if (!defined $Lex{$ling}) {
       $i=1;
   }
   $Rank{$ling}{$term} = $i;
   $Lex{$ling}{$term} = $term;
   $i++;
   #   print STDERR "#$term# #$ling#\n" if ($term eq "artículo");
}


while (my $line = <S>) {
   chomp $line;
  ($suffix, $ling) = split ("\t", $line);

   $Suffix{$ling}{$suffix}++;
  # $Lex{$ling}{$suffix} = $term;
  #print STDERR "#$suffix# #$ling#\n";
}


while (my $line = <STDIN>) {
  chomp $line;
  my $line_orig = $line;
 # if (!$line){next}
  $line =~ s/($Separador)/ $1 /g;
  $line = lc($line);
  my $found=0;
  my %Peso;
  print "$line_orig\t";
  (my @ListaDeTokens) = split(" ", $line);
  foreach my $token (@ListaDeTokens) {
    ##change uppercase to lowercase:
    # print STDERR "tok: #$token# :: \n" if ($token eq "artículo" && $Rank{"es"}{"artículo"} );
    $token = lc ($token);
    if ($token !~ /$Separador/) {
       foreach $ling (keys %Lex) {
        #if ($Lex{$ling}{$token} =~ /^$token$/i) {
         if (defined $Lex{$ling}{$token}) {
           $Peso{$ling} += $i - $Rank{$ling}{$token} ;
           # print STDERR "lex: #$ling# :: #$token# #$Peso{$ling}# #$i# # $Rank{$ling}{$token} # \n";
           $found=1;
         } 
           
         else {
           
	   foreach $s (keys %{$Suffix{$ling}}) {
                 #print STDERR "lex: #$ling# :: #$token# #$Peso{$ling}# #$s# \n";
                 if ($token =~ /$s$/) {
                     $Peso{$ling} += $i - ($i/2) ;
                     #print STDERR "lex: #$ling# :: #$token# #$Peso{$ling}# #$i# \n";
                   
		 }
	   }
	 }
      }
    }
  }
  if (!$found && $line eq ""){
    print "$ling_def_1\n"; 
  }
  elsif (!$found){
    print "$ling_def_2\n";
  }
  else {
  my $First=0;
  foreach $ling (sort {$Peso{$b} <=>
                      $Peso{$a} }
		 keys %Peso ) {
 "------------->$ling - $Peso{$ling}\n";
    if (!$First) {
      print "$ling\n";
      $First=1;
  
    }
   }
  }
}

#print STDERR "esp = $esp || gal = $gal\n";

##default:


   



