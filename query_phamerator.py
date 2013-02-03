#!/usr/bin/env python
import os,time,sys
from datetime import datetime
import MySQLdb as mysql
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO

#Connect to the MySQL database. Change values if necessary.
db = mysql.connect(host='localhost',user='root',passwd='phage',db='Mycobacteriophage_Database')

#The main data retrieval class
class Query:
	"""Class for searching for retrieving FASTA files for phamerator queries.

	Methods:
	disp_query
	main_menu
	menu_options
	log
	make_fasta_files
	run_search
	start

	"""
	def __init__(self, id, phages=None,clusters=None,phams=None,aa=True):
		"""Initialize the Query class.
		id (int) (required) A unique id for the query
		phages (list) (optional) A list of phages to search for
		clusters (list) (optional) A list of clusters to search for
		phams (list) (optional) A list of phams to search for 
		aa (Boolean) (optional) Boolean to search for amino acid sequences (True) or nucleotide sequences (False)
		
		"""

		if phages is None:
			phages = []

		if clusters is None:
			clusters = []

		if phams is None:
			phams = []

		self.id = id
		self.phages = phages
		self.clusters = clusters
		self.phams = phams
		self.aa = aa
		#self.gene_list (populated by self.run_search()) is a dictionary of the format {<PhageID or pham#>:[<list of GeneIDs>]}
		self.gene_list={}
		#User organization preference
		self.organization=0
		#Basic logging
		self.log("Query started.")

	def disp_query(self):
		"""Display the current search parameters"""
		print "Current search parameters","Phages:",self.phages,"Clusters:",self.clusters, "Phams:",self.phams
		if self.aa: print "Retrieving Amino Acids"
		else: print "Retrieving Nucleotides"

	def main_menu(self):
		"""Initialize and display the main menu"""
		self.disp_query()
		print "Query ID: %s"%self.id
		print "Add search parameters\n[0] Phage Name(s)\n[1] Cluster(s)\n[2] Pham(s)\nRemove search parameters\n[3] Phage Name(s)\n[4] Cluster(s)\n[5] Pham(s)\nOther options\n[6] Toggle Amino Acids/Nucleotides\n[7] Search\n[8] Reset\n[9] Quit"
		#Process selected option
		try:
			self.menu_options(raw_input("Select option: "))
		except Exception as error:
			print "Sorry, an unexpected error occurred. Please restart the program and try again. The error has been logged."
			self.log("ERROR: %s"%error)

	def menu_options(self, param):
		"""Process selections from the main menu.

		Arguments:
		'param' (str) (required) The user selected menu option
		"""
		#raw_input() returns a str value that must be converted to int
		try:
			param = int(param)
			range(10).index(param)
		except ValueError as error:
			print "Sorry, you have not chosen a valid menu option."		
			self.log("ERROR: %s"%error)
			self.menu_options(raw_input("Select option: "))	
		#Menu options 0-5 split the user input at commas and store the result in the appropriated search paramater
		if param == 0:
			for i in raw_input("Enter one or more phage names separated by a comma: ").split(","):
				self.phages.append(i.strip())
			print self.phages
		if param == 1:
			for i in raw_input("Enter one or more clusters separated by a comma:").split(","):
				self.clusters.append(i.strip())
			print self.clusters
		if param == 2:
			for i in raw_input("Enter one or more phams separated by a comma:").split(","):
				self.phams.append(i.strip())
			print self.phams
		if param == 3:
			print self.phages
			for i in raw_input("Enter one or more phages to remove separated by a comma: ").split(","):
				self.phages.remove(i.strip())
			print self.phages
		if param == 4:
			print self.clusters
			for i in raw_input("Enter one or more clusters to remove separated by a comma: ").split(","):
				self.clusters.remove(i.strip())
			print self.clusters
		if param == 5:
			print self.phams
			for i in raw_input("Enter one or more phams to remove separated by a comma: ").split(","):
				self.phams.remove(i.strip())
			print self.phams
		#Option 6 toggles the variable self.aa. True->False, False->True.
		if param == 6:
			self.aa = not self.aa
			print "Successfully toggled"
		#Option 7 calls the function to run the search
		if param == 7:
			self.run_search()
		#Option 8 resets the search parameters
		if param == 8:
			self.log("Query exited.")
			print "Resetting search..."
			try:
				start({})
			except Exception as error:
				print "Sorry, an unexpected error has occured. Please restart the program and try again. The error has been logged."
				self.log("Error: %s"%error)
		#option 9 exits the program
		if param == 9:
			self.log("Query exited.")
			quit()
		#Display the main menu
		try:
			self.main_menu()
		except Exception as error:
			print "Sorry, an unexpected error has occured. Please restart the program and try again. The error has been logged."
			self.log("Error: %s"%error)

	def log(self,logtext):
		"""Write text to log file.

		Arguments:
		'logtext' (str) (required) The text to be logged.

		"""
		if not os.path.exists("FASTA-files"): os.makedirs("FASTA-files")
		if not os.path.exists(os.path.join("FASTA-files","logs")): os.makedirs(os.path.join("FASTA-files","logs"))	
		f = open(os.path.join("FASTA-files","logs","%s.txt"%self.id),"a")
		dtime = datetime.now().strftime("%Y-%M-%d %H:%m:%S")
		#Logs are of the format [Timestamp] Query id: Log text
		log = "[%s] %s: %s\n" % (dtime,self.id,logtext)
		f.write(log)
		f.close()

	def make_fasta_files(self,o):
		"""Write gene information to FASTA files"""
		#Create a database instance
		cursor = db.cursor()
		#Create directory "FASTA-files" if it does not already exist
		if not os.path.exists("FASTA-files"): os.makedirs("FASTA-files")
		#Convert the id to a string
		id_str = str(self.id)
		#Create directory <id_str> if it does not already exist
		if not os.path.exists(os.path.join("FASTA-files",id_str)):os.makedirs(os.path.join("FASTA-files",id_str))
		#The FASTA files will be output to "FASTA-files/<id_str>"

		#Iterate through <self.gene_list> (generated by self.run_search())
		for name,gene_list in self.gene_list.items():
			#Create a local list to store  gene information
			recs=[]
			if o==0:
				#Retrieve cluster information if necessary
				query = "SELECT Cluster FROM phage WHERE name='%s'"%name
				self.log("Query executed: %s"%query)
				cursor.execute(query)
				cluster = cursor.fetchone()[0]
				cluster = "Singleton" if cluster==None else cluster
			#Iterate through list of genes
			for g in gene_list:
				if not self.aa:
					#Unlike amino acid sequences, nucleotide sequences for genes are not stored in the 'gene' table. The phage's nucleotide sequence must be retrieved. Sequences for specific genes are extracted using the start and stop codon values stored in the 'gene' table
					query = "SELECT sequence FROM phage WHERE PhageID=ANY(SELECT DISTINCT(PhageID) FROM gene WHERE GENEID='%s')"%g
					self.log("Query executed: %s"%query)
					cursor.execute(query)
					n_seq = cursor.fetchone()[0]
				#Retrieve the PhageID, gene name, start position, stop position, start codon, stop codon, orientation, and amino acid sequence for each gene in <gene_list>. 
				query = "SELECT PhageID,Name,Start,Stop,StartCodon,StopCodon,Orientation,Translation FROM gene WHERE GeneID='%s'"%g
				self.log("Query executed: %s"%query)
				cursor.execute(query)
				#Iterate through the results
				for r in cursor.fetchall():
					if self.aa:
						#Store amino acid sequence as 'Seq' type from BioPython. 
						seq = Seq(r[7],IUPAC.protein)
						#Record information about the gene, including the gene id, the phage name (PhageID), and a basic description.
						this_rec=SeqRecord(seq,id="%s|"%(r[1]),name=r[0],description="Amino acid sequence of gene %s from phage %s|%s|%s|%s"%(r[1],r[0],r[6],r[2],r[3]))
					else:
						#Store nucleotide sequence as 'Seq' type from BioPython. <r[2]> and <r[3]> reference the start and stop positions of the gene. 
						seq = Seq(n_seq[r[2]:r[3]],IUPAC.unambiguous_dna)
						#Corrects nucleotide sequence of genes that overlap the origin of replication
						if r[2]>r[3]:
							seq = Seq(n_seq[r[2]:]+n_seq[:r[3]], IUPAC.unambiguous_dna)
						if r[6]=="F":
							this_rec=SeqRecord(seq,id="%s|"%(r[1]),name=r[0],description="Nucleotide sequence of gene %s from %s|%s|%s|%s"%(r[1],r[0],r[6],r[2],r[3]))
						#Translate the gene if it is a reverse gene
						elif r[6]=="R":
							this_rec=SeqRecord(seq.reverse_complement(),id="%s|"%(r[1]),name=r[0],description="Nucleotide sequence of gene %s from %s|%s|%s|%s"%(r[1],r[0],r[6],r[2],r[3]))
					#Append the current <this_rec> to the list of <recs> for the current phage or pham (<p>)
					recs.append(this_rec)
			#Organized by phage
			if o==0:
				#Create folder structure. FASTA files will be stored in 'FASTA-files/<cluster>/(<subcluster>/)<name>.fasta'			
				if cluster == 'Singleton':
					if not os.path.exists(os.path.join("FASTA-files",id_str,'Singleton')):os.makedirs(os.path.join("FASTA-files",id_str,"Singleton"))
					file_name = os.path.join("FASTA-files",id_str,"Singleton","%s.fasta"%name)
				else:
					if not os.path.exists(os.path.join("FASTA-files",id_str,cluster[0])):os.makedirs(os.path.join("FASTA-files",id_str,cluster[0]))
					if len(cluster)>1:
						if not os.path.exists(os.path.join("FASTA-files",id_str,cluster[0],cluster)):os.makedirs(os.path.join("FASTA-files",id_str,cluster[0],cluster))
						#The filename and path for the phage's fasta file
						file_name = os.path.join("FASTA-files",id_str,cluster[0],cluster,"%s.fasta"%name)
					else:
						file_name = os.path.join("FASTA-files",id_str,cluster[0],"%s.fasta"%name)
				#Write the gene information to a fasta file. SeqIO.write() returns an int of the number of genes recorded.
				write_fasta = SeqIO.write(recs,file_name,"fasta")
				#Tell the user where to find the fasta file and how many genes were recorded
				print "Phage %s's FASTA file created in %s. %s genes logged\n"%(name,file_name,write_fasta)
			#Organized by pham
			else:
				#Filename and path for the pham's fasta file
				file_name = os.path.join("FASTA-files",id_str,"%s.fasta"%name)
				write_fasta = SeqIO.write(recs,file_name,"fasta")
				print "Pham %s's FASTA file created in %s. %s genes logged\n"%(name,file_name,write_fasta)
		#Begin a new query with the current search parameters
		try:
			start({"phages":self.phages,"clusters":self.clusters,"phams":self.phams,"aa":self.aa})
		except Exception as error:
			print "Sorry an unexpected error has occured. Please restart the program and try again. The error has been logged."
			self.log("ERROR: %s"%error)
			raise
	def run_search(self):
		#Should the results be sorted by phage or by pham?
		try:
			o = int(raw_input("[0] Phage\n[1] Pham\nOrder FASTA files by: "))
			range(2).index(0)
		except ValueError as error:
			print "Sorry, you have entered an invalid option. Please try again."
			self.log("Error: %s"%error)
			self.run_search()
		except Exception as error:
			print "Sorry an unexpected error has occured. Please restart the program and try again. The error has been logged."
			self.log("ERROR: %s"%error)			
		#Begin to build query. Will return a list of PhageIDs
		query = "SELECT DISTINCT(PhageID),cluster,name FROM phage"
		#Expand cluster list into list of subclusters
		cursor = db.cursor()
		cluster_list = set()
		if len(self.clusters)>0:
			query += " WHERE "
			for c in self.clusters:
				if c != "Singleton":
					#Search for all clusters that are similar to each user defined cluster (e.g. 'F' becomes ['F1','F2'])
					c_query = "SELECT DISTINCT(Cluster) FROM phage WHERE Cluster LIKE '{}%'".format(c)
					self.log("Query executed: %s"%c_query)
					cursor.execute(c_query)
					results = cursor.fetchall()
					#Iterate over the retrieved subclusters
					for i in results:
						#Add results to a new list of clusters and subclusters if they do not already exist
						cluster_list.add(i)
			if len(cluster_list)>0:
				#Accounts for quirk in tuple->str conversion: str(('x')) = 'x'. str(('x','y')) = "('x','y')"
				cluster_list=tuple(cluster_list)
				if len(cluster_list)==1:
					cluster_list="('%s')"%cluster_list[0]
				elif len(cluster_list)>1:
					cluster_list=str(cluster_list)
				#Add cluster parameters to query
				query += "Cluster IN %s"%cluster_list

		if "Singleton" in self.clusters:
			if len(cluster_list)>0:
				query += "OR "
			#Singletons are stored in the 'phage' table with a NULL value in the 'cluster' column.
			query += "cluster IS NULL"

		if len(self.phages)>0 and len(self.clusters)>0:
			query += " OR "
		elif len(self.phages)>0 and len(self.clusters)==0:
			query += " WHERE "
		#Add phage parameters to query
		if len(self.phages)==1:
				query += "Name='%s'"%self.phages[0]
		elif len(self.phages)>1:
				query += "Name IN %s"%str(tuple(self.phages))
		self.log("Executed query: %s" % query)
		cursor.execute(query)
		#Iterate through results. Will retrieve list of genes for each PhageID returned with the previous query
		for r in cursor.fetchall():
			#Store cluster information in a local variable
			cluster = "Singleton" if r[1] is None else r[1]
			#Begin building query. Will return a list of GeneIDs
			query = "SELECT GeneID,pham.name FROM gene JOIN pham USING (GeneID) WHERE PhageID='%s'"%r[0]
			if len(self.phams)==1:
				query += " AND pham.name='%s'"%self.phams[0]
			elif len(self.phams)>1:
				query += " AND pham.name IN %s"%str(tuple(self.phams))
			#Order genes by start position
			query += " ORDER BY start"
			self.log("Executed query: %s"%query)
			cursor.execute(query)
			#Iterate through the list of GeneIDs
			for g in cursor.fetchall():
				#If organizing by phage
				if o==0:
					#Store a list of genes as a dictionary value corresponding to the appropriate dictionary key. <r[0]> corresponds to the name of the phage
					if r[2] in self.gene_list:
						self.gene_list[r[2]].append(g[0])
					else:
						self.gene_list[r[2]]=[g[0]]
				#If organizing by pham		
				else:
					#Store a list of genes a a dictionary value corresponding to the appropriate dictionary key <g[1]> corresponds to the pham number
					if g[1] in self.gene_list:
						self.gene_list[g[1]].append(g[0])
					else:
						self.gene_list[g[1]]=[g[0]]

		#Close database connection
		cursor.close()
		print "Query complete."
		#Create the FASTA files
		try:
			self.make_fasta_files(o)
		except Exception as error:
			print "Sorry an unexpected error has occured. Please restart the program and try again. The error has been logged."
			self.log("ERROR: %s"%error)
			raise
def start(options={}):
	"""Initialize a query and display the main menu."""
	try:
		#time.time() resturns the current Unix timestamp.
		q = Query(time.time(),**options)
		q.main_menu()
	except Exception as error:
		print "Sorry an unexpected error has occured. Please restart the program and try again. The error has been logged."
		self.log("ERROR: %s"%error)
		raise

#Start the program
if __name__ == '__main__':
	start()