import time
import math
import sptensor.morton as mort

NBUCKETS = 128

class HashTable:
	def __init__(self, nbuckets):
		self.nbuckets = nbuckets
		self.morton = [None] * nbuckets
		self.key = [0] * nbuckets
		self.value = [0.0] * nbuckets
		self.idx = [None] * nbuckets
		self.flag = [0] * nbuckets
		self.bits = int(math.ceil(math.log2(self.nbuckets)))
		self.sx = int(math.ceil(self.bits/8)) - 1
		self.sy = 4*self.sx - 1 
		if self.sy < 1:
			self.sy = 1
		self.sz = int(math.ceil(self.bits/2))
		self.mask = ~(self.nbuckets-1)
		self.num_collisions = 0
		self.num_accesses = 0
		self.num_probe = 0
		self.probe_time = 0.0

	def __iter__(self):
		self.a = self.hashtable.value[0]
		self.i = 0
		return self

	def __next__(self):
		if self.i < self.nbuckets:
			self.a = self.hashtable.value[self.i]
			self.i += 1
			return self.a
		else:
			raise StopIteration
			
	def hash(self, idx):
		"""
		Hash the index and return the morton code and key.

		Parameters:
			idx - The index to hash

		Returns:
			morton, key
		"""
		m = mort.morton(*idx)
		hash = m
		hash += hash << self.sx
		hash ^= hash >> self.sy
		hash += hash << self.sz
		k = hash % self.nbuckets
		return m, k
	

	def probe(self, morton, key):
		"""
		Probe for either a matching index or an empty position.

		Parameters:
			morton - Morton code of the index
			key - The hashed key of this item.

		Returns:
			The index of either an empty bucket or the matching entry.
		"""

		# count the accesses
		self.num_accesses = self.num_accesses + 1
		i = key

		# check for collision
		if self.flag[i] != 0 and self.morton[i] != morton:
			self.num_collisions = self.num_collisions + 1
		while True:
			if self.flag[i] == 0 or self.morton[i] == morton:
				return i
			i = (i+1) % self.nbuckets
			self.num_probe = self.num_probe + 1



class hash_t:
	def __init__(self, modes=None):
		#Hash specific fields
		self.hashtable = HashTable(NBUCKETS)
		self.hash_curr_size = 0
		self.load_factor = 0.7

		#sptensor fields
		self.modes = modes
		if modes:
			self.nmodes = len(modes)
		else:
			self.nmodes = 0
	

	#Function to insert an element in the hash table. Return the hash item if found, 0 if not found.
	def set(self, i, v):
		# build the modes if we need
		if not self.modes:
			self.modes = [0] * len(i)
			self.nmodes = len(i)
		
		# update any mode maxes as needed
		for m in range(self.nmodes):
			if self.modes[m] < i[m]:
				self.modes[m] = i[m]

		# hash the item
		morton, key = self.hashtable.hash(i)
		index = self.hashtable.probe(morton, key)

		# either set or clear the item
		if v != 0:
			#set the value
			self.hashtable.value[index] = v

			# handle new assignments
			if self.hashtable.flag[index] == 0:
				# mark as present
				self.hashtable.flag[index] = 1

				# handle hash information
				self.hashtable.morton[index] = morton
				self.hashtable.key[index] = key

				# copy the value and index
				self.hashtable.idx[index] = tuple(i)

				# Increase hashtable count
				self.hash_curr_size = self.hash_curr_size + 1
		else:
			# check if item is present in the table
			if self.hashtable.flag[index] == 1:
				# remove it from the table
				#self.remove(i)
				pass

		# Check if we need to rehash
		if((self.hash_curr_size/self.hashtable.nbuckets) > 0.8):
			self.rehash()

		return

	def get(self, i):
		# get the hash item
		morton, key = self.hashtable.hash(i)
		i = self.hashtable.probe(morton, key)

		# return the item if it is present
		if self.hashtable.flag[i] == 1:
			return self.hashtable.value[i]
		else:
			return 0.0


	def clear(self, ):
		for i in range(self.nbuckets):
			self.hashtable.flag[i] = 0
		return


	def rehash(self):

		# Double the number of buckets
		new_hash_size = self.hashtable.nbuckets * 2
		new_hashtable = HashTable(new_hash_size)

		#save the old hashtable
		old_hashtable = self.hashtable

		# install the new one
		self.hashtable = new_hashtable

		# Rehash all existing items in t's hashtable to the new table
		for i in range(old_hashtable.nbuckets):
			#if occupied, we need to copy it to the other table!
			if(old_hashtable.flag[i] == 1):
				self.set(self.hashtable.idx[i], self.hashtable.value[i])


	def remove(self, idx):
		done = 0

		# get the index
		morton, key = self.hashtable.hash(idx)
		index = self.hashtable.probe(morton, key)

		i = self.hashtable.key[index]
		j = i+1

		# slide back as needed
		while(done == 0):
			# assume we are done
			done=1

			# mark as not present
			self.hashtable.flag[i] = 0

			# go to the next probe slot
			j = (i+1)%j

			# check to see if we need to slide back
			if(self.hashtable.flag[j] == 0):
				continue

			# check to see if this one should be pushed back
			if (self.hashtable.key[j] == self.hashtable.key[j]):
				#print('key[i] == key[j]')
				done = 0
				self.hashtable.flag[i] = self.hashtable.flag[j]
				self.hashtable.morton[i] = self.hashtable.morton[j]
				self.hashtable.value[i] = self.hashtable.value[j]
				self.hashtable.idx[i] = self.hashtable.idx[j]

			# go on for the next one */
			i=j


	def nnz(self):
		print('to be implemented')


	def get_slice(self, key):
		# make it a list!
		key = list(key)

		# convert all keys into ranges and extract modes
		resultModes = []
		for i in range(len(key)):
			if type(key[i]) == slice:
				key[i] = range(*key[i].indices(self.modes[i]))
			else:
				key[i] = range(key[i], key[i]+1)
			resultModes.append(len(key[i]))

		# create the result tensor
		result = hash_t(resultModes)

		# copy the relevant non-zeroes
		for index in range(self.hashtable.nbuckets):
			#skip the not-present
			if self.hashtable.flag[index] != 1:
				continue

			# copy the things in our range
			copy = True
			for i in range(len(self.hashtable.idx[index])):
				if self.hashtable.idx[index][i] not in key[i]:
					copy = False
					break
			if copy:
				result.set(self.hashtable.idx[index], self.hashtable.value[index])
		return result


	def __getitem__(self, key):
		# make the key iteratble (if needed)
		if not hasattr(key, '__iter__'):
			key = (key,)

		# validate the index
		if len(key) != self.nmodes:
			raise IndexError("Mode Mismatch")
		simpleIndex = True
		for i in key:
			if type(i)==slice:
				simpleIndex = False
			elif type(i) != int:
				raise IndexError("Mode index must be either a slice or an integer.")

		# handle simple index
		if simpleIndex:
			return self.get(key)

		# do the extra work
		return self.get_slice(key)


	def __setitem__(self, key, value):
		# make the key iteratble (if needed)
		if not hasattr(key, '__iter__'):
			key = (key,)

		# validate the index
		if len(key) != self.nmodes:
			raise IndexError("Mode Mismatch")
		for i in key:
			if type(i) != int:
				raise IndexError("Mode index must be an integer.")

		self.set(key, value)

def read(file):
	count=0
	with open(file, 'r') as reader:
		# Create the tensor
		tns = hash_t()

		for row in reader:
			#print(count)
			count=count+1
			if count % 1000 == 0:
				print("Count: ", count, "Collisions:", tns.num_collisions, "Probes:", tns.num_probe)
			row = row.split()
			# Get the value
			val = float(row.pop())
			# The rest of the line is the indexes
			idx = [int(i) for i in row]

			tns.set(idx, val)

	reader.close()
	return tns

def write(file, tns):

	# print the preamble
	print(tns.nmodes, end=' ')
	for i in range(tns.nmodes):
		print(tns.modes[i], end=' ')

	print('\n',end='')

	for i in range(tns.hashtable.nbuckets):
		if tns.hashtable.flag[i] == 1:
			# print the indexes
			for j in range(tns.nmodes):
				print(tns.hashtable.idx[i][j], end=' ')

			#print the value
			print(tns.hashtable.value[i])
