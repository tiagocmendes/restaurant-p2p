# drive-through-p2p

This repository implement a drive-through restaurant using a [peer-to-peer](https://pt.wikipedia.org/wiki/Peer-to-peer) distributed system architecture.  

## Problem description
This restaurant simulation is composed by five different entities:  

* **Restaurant:** entity responsible for managing all kitchen equipment (fryer, barbecue griller and bar).
* **Clerk:** receives the clients and records their requests.
* **Chef:** receives the requests and cooks them.
* **Waiter:** delivers the order to the respective client and receives payment.
* **Client:** makes a food request.

This entities are organized in a token-ring.

The kitchen is composed by 3 equipments:

* **Barbecue griller:** where the Chef can prepare one hamburger (average preparing time: 3 seconds)
* **Bar:** where the Chef can prepare one drink (average preparing time: 1 second)
* **Fryer:** where the Chef can prepare one package of fries (average preparing time: 5 seconds)

Each action takes a random time to be completed. This random time follows a gaussian distribution with an average time of 2 seconds and a standar deviation of 0.5 seconds.
One client request is composed by at least one item (hamburger, drink or package of fries), but can be one possible combination of items with a maximum of 5 items. This request is generated randomly.

## How to run
* If you want to run the solution with the Restaurant access port:  
```console
$ ./run.sh
```

* If you want to run the solution with a random access port:  
```console
$ ./run_random.sh
```

## Useful links
**Work objectives:** [CD2019A01.pdf](https://github.com/detiuaveiro/drive-through-p2p-tiagocmendes/blob/master/CD2019A01.pdf)  
**Token ring:** [https://en.wikipedia.org/wiki/Token_ring](https://en.wikipedia.org/wiki/Token_ring)  
**Python - random:** [https://docs.python.org/3/library/random.html#module-random](https://docs.python.org/3/library/random.html#module-random)  
**Python - time:** [https://docs.python.org/3/library/time.html#time.sleep](https://docs.python.org/3/library/time.html#time.sleep)  
**Python - logging:** [https://docs.python.org/3/library/logging.html?highlight=log#module-logging](https://docs.python.org/3/library/logging.html?highlight=log#module-logging)  
**Python - pickle:** [https://docs.python.org/3/library/pickle.html](https://docs.python.org/3/library/pickle.html)  
**Python - Socket programming:** [https://docs.python.org/3/howto/sockets.html](https://docs.python.org/3/howto/sockets.html)  

## Authors
This project was developed under the [Distributed Computation](https://www.ua.pt/ensino/uc/12273) course of [University of Aveiro](https://www.ua.pt/).

* **João Vasconcelos**: [jmnmv12](https://github.com/jmnmv12)
* **Tiago Mendes**: [tiagocmendes](https://github.com/tiagocmendes)

**April, 2019**
