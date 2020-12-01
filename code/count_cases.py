#!/usr/bin/python
import bisect
import gzip
import optparse

#Parse options
parser = optparse.OptionParser()
parser.add_option("-s", "--snpfile", action="store",dest="snpfilename") #File matching SNPs to genes
parser.add_option("-v", "--vcffile", action="store",dest="vcffilename") #Path to vcf file
parser.add_option("-o", "--outfile", action="store",dest="outfilename", default="case_counts.txt") #Output file name 

parser.add_option("--snpformat", action="store",dest="snpformat", default="CHRPOSREFALT") #Field in which to get SNP names. If not VCF ID, then CHR:POS:REF:ALT is used
parser.add_option("--samplefile", action="store",dest="samplefilename", default="ALL")

#Optional Filters
parser.add_option("--pass", action="store_true", dest="passfilter")
parser.add_option("--maxAF", action="store",dest="maxAF", default=1)
parser.add_option("--maxAC", action="store",dest="maxAC", default=99999)
parser.add_option("--minAN", action="store",dest="minAN", default=0)
parser.add_option("--GTfield", action="store",dest="gtfield", default="GT")
parser.add_option("--bedfile", action="store", dest="bedfilename")

options, args = parser.parse_args()

#Try to catch potential errors
if not options.snpfilename:   # if filename is not given
    parser.error('A file containing a list of SNPs is needed')

if not options.vcffilename:   # if vcf filename is not given
    parser.error('A vcf file is needed')

if options.vcffilename.endswith(".gz") is False:   # if vcf filename is not given
    parser.error('Is your vcf file gzipped?')

vcffile=gzip.open(options.vcffilename, "rb")
chrformat="number"
for line_vcf1 in vcffile:
	line_vcf=line_vcf1.split("\t")
	if "##contig" in line_vcf[0]:
		if "ID=chr" in line_vcf[0]:
			chrformat="chr"
	elif line_vcf[0]=="#CHROM":
		#This takes the vcf header line and finds the indices corresponding to the individuals present in the sample file
		samplenames=line_vcf[9:]

		#If User doesn't provide sample list, assume all samples in vcf
		if options.samplefilename=="ALL":
			sampleindices=range(0, len(samplenames),1)

		#else, find the indices corresponding to the samples in the user-provided list
		else:
			#Generate sample list
			sample_list=[]
			sample_file=open(options.samplefilename, "r")
			for line_s1 in sample_file:
        			sample_list.append(line_s1.rstrip())
			sample_file.close()
			sampleindices=[i for i,val in enumerate(samplenames) if str(val) in sample_list]
		break
vcffile.close()

#Functions
def findcarriers(vcfline, gtname, snpformat, samplelist, max_ac, max_af, min_an):
	#Find the column in the genotype field corresponding to the genotypes
	gtcol=vcfline[8].split(":").index(gtname)

	if snpformat=="VCFID":
		snpid=vcfline[2]
	else:
		snpid=str(vcfline[0]).lstrip("chr")+":"+str(vcfline[1])+":"+str(vcfline[3])+":"+str(vcfline[4])
	
	#Extract genotypes 
	gt=[i.split(':')[gtcol] for i in vcfline[9:]]

	#Find carriers
	hets=[i for i,val in enumerate(gt) if str(val) in ["0/1", "1/0", "0|1", "1|0"]]
	hetcarriers=list(set(hets) & set(samplelist))
	homs=[i for i,val in enumerate(gt) if str(val) in ["1/1", "1|1"]]
	homcarriers=list(set(homs) & set(samplelist))
	
	ac_file=(float(len(hets)+2*len(homs)))
	af_file=ac_file/(2*(float(len(gt))))
	an_file=2*(float(len(gt)))
	
	if (ac_file>float(max_ac)) or (af_file>float(max_af)) or (an_file<float(min_an)):
		return [[],[], 0]
	else:
		ac_out=len(hets)+(2*len(homs))
		return [hetcarriers, homcarriers, ac_out]


def makesnplist(snpfile):
	#Makes a list of SNPs present in the snpfile
	snplist=[]
	#Read in snpfile
	snp_file=open(snpfile, "r")
	
	for line_snp1 in snp_file:
		line_snp=line_snp1.rstrip('\n').split('\t')

		#Find column corresponding to desired snps
		if line_snp[0]!="GENE":
			snplist=snplist+line_snp[1].split(",")
	return set(snplist)
	snp_file.close()


def calculatecount(genesnps, snptable):
	#This will generate an aggregate count for a given gene.
        all_index=[]
	het_index=[]
	hom_index=[]
	total_ac=0
        for s in range(0, len(genesnps), 1):
                if genesnps[s] in snptable:
                        tempsnp=genesnps[s]
			het_index=het_index+snptable[tempsnp][1]
	                hom_index=hom_index+snptable[tempsnp][2]
			total_ac=total_ac+snptable[tempsnp][3]
	all_index=het_index+hom_index
			
	#Generate number of individuals carrying one variant
        count_het=len(set([x for x in het_index if het_index.count(x) > 0]))
	count_ch=len(set([x for x in het_index if het_index.count(x) > 1]))
        count_hom=len(list(set(hom_index)))
	return [count_het, count_ch, count_hom, total_ac]

#Make list of all SNPs across all genes present in snpfile
allsnplist=makesnplist(options.snpfilename)

#Make a hashtable with keys as each SNP, and stores a list of indices of carriers for that SNP
count_table={} 


#read in bedfile
if options.bedfilename is not None:
	if str(options.bedfilename).endswith(".gz") is True:
		bed=gzip.open(options.bedfilename, "rb")
	else:
		bed=open(options.bedfilename, "r")
	bed_lower={}
	bed_upper={}
       	for line_b1 in bed:
                line_b=line_b1.rstrip().split('\t')
                chr=str(line_b[0]).lower().replace("chr", "")
		if chr not in bed_lower:
			bed_lower[chr]=[chr, []]
			bed_upper[chr]=[chr, []]
                bed_lower[chr][1].append(int(line_b[1])+1)
                bed_upper[chr][1].append(int(line_b[2]))
	bed.close()	

vcffile=gzip.open(options.vcffilename, "rb")
		
for line_vcf1 in vcffile:
	line_vcf=line_vcf1.rstrip().split('\t')
	if line_vcf[0][0]!="#" and ("," not in line_vcf[4]):
		keep=1
		#Subset on bedfile
		if options.bedfilename is not None:
			chr=str(line_vcf[0]).lower().replace("chr", "")
			temp_index=bisect.bisect(bed_lower[chr][1], int(line_vcf[1]))-1
			if temp_index<0:
				keep=0	 
			elif int(line_vcf[1])>bed_upper[chr][1][temp_index]:
				keep=0
		if not (options.passfilter and line_vcf[6]!="PASS"):
			if options.snpformat=="VCFID":
				snpid=str(line_vcf[2])
			else: 
				snpid=str(line_vcf[0]).lower().replace("chr", "")+":"+str(line_vcf[1])+":"+str(line_vcf[3])+":"+str(line_vcf[4])
			if (snpid in allsnplist) and (keep==1):
				counts=findcarriers(line_vcf, options.gtfield, options.snpformat, sampleindices, options.maxAC, options.maxAF, options.minAN)
				if counts[2]>0:
					count_table[snpid]=[snpid, counts[0], counts[1], counts[2]]
vcffile.close() 


#Generate output counts
outfile=open(options.outfilename, "w")
outfile.write("#GENE\tCASE_COUNT_HET\tCASE_COUNT_CH\tCASE_COUNT_HOM\tCASE_TOTAL_AC\n")
snpfile=open(options.snpfilename, "r")
for line_s1 in snpfile:
	line_s=line_s1.rstrip('\n').split('\t')
	if line_s[0][0]!="#":
		genesnplist=list(set(line_s[1].split(',')))
		counts=calculatecount(genesnplist, count_table)
		outfile.write(line_s[0]+"\t"+str(counts[0])+"\t"+str(counts[1])+"\t"+str(counts[2])+"\t"+str(counts[3])+'\n')
outfile.close()
snpfile.close()

#python count_case.py -s test.out.txt -o counts.txt -v test.ihh.vcf.gz --snpformat CHRPOSREFALT
