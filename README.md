NotEnoughBogo [![Build Status](https://travis-ci.org/matiaslindgren/not-enough-bogo.svg?branch=master)](https://travis-ci.org/matiaslindgren/not-enough-bogo)
=============================================================================================================================================================

This project aims to benchmark performance of an unoptimized, randomized and unstable [bogosort](https://en.wikipedia.org/wiki/Bogosort).
Progress will be monitored and plotted.
The project will be deployed to the cloud and benchmarking is continued until a sequence of 2080 integers is sorted or the destruction of ~~THE UNIVERSE~~ ~~the human race~~ ~~the internet~~ my motivation occurs.

2080?
-----
Python's [random-module](https://docs.python.org/3/library/random.html) utilizes the [Mersenne Twister](https://en.wikipedia.org/wiki/Mersenne_Twister) for pseudo-random number generation, which has quite an impressive period of 2^19937-1, which is about 4.3\*10^6001.
However, the amount of possible permutations of a sequence of 2081 integers is even more impressive at about 4.1\*10^6003, while 2080! is outright pathetic at about 2.0\*10^6000.
This implies that [random.shuffle](https://docs.python.org/3/library/random.html#random.shuffle) cannot generate every permutation of a sequence containing more than 2080 elements.
Needless to say, this also implies that the unoptimized, randomized and unstable bogosort algorithm implemented in this project is not anymore guaranteed to produce a solution if the lists being sorted exceed 2080 elements.
This in turn, of course, implies that attempting to sort lists containing more than 2080 elements is a complete waste of time and resources so it shall not be attempted.

See also the Wikipedia article on [pseudorandom generators](https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle#Pseudorandom_generators:_problems_involving_state_space.2C_seeding.2C_and_usage)
