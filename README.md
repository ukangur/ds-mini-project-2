# Distributed Systems (Spring 2022)

## Mini-project 2: The Byzantine General’s problem with Consensus
### Authors: Markus Punnar and Uku Kangur

This project implements the the Byzantine General’s problem in Python using distributed threaded nodes. The project composes of four files:

<ol>
  <li>main.py - starts the program and handles the user given input commands</li>
  <li>node.py - holds the threaded node class, which is used to initialize and do operations with the nodes</li>
  <li>nodeconnection.py - holds information about node connections and is used to pass messages between nodes</li>
  <li>example video.mp4 - 1 minute video example of using the program</li>
</ol>

The node.py and nodeconnection.py class structure is based on https://github.com/macsnoeren/python-p2p-network

## Starting the program

To run the program you must enter into console

```console
python main.py <THREAD COUNT>
```

Here \<THREAD COUNT\> marks the number of nodes (generals) that the system uses. All new nodes are added with the default status of being non-faulty. After the node connections have been made, the program randomly elects a primary node and you can start giving commands.

## Possible commands

### g-state

The "g-state" command prints all of the nodes with their ID-s and status. An example:

G1, primary, state=NF

G2, secondary, state=NF

G3, secondary, state=F

G4, secondary, state=NF

### g-state \<ID\> \<STATE\>
  
This command changes the node at ID to the given state. There are only two valid states: faulty and non-faulty.
  
### g-add \<NODE COUNT\>
  
This command add the given amount of nodes (generals) to the system. These nodes are non-faulty by status and secondary by role.

### g-kill \<ID\>

This command kills and removes the command with the given ID.

### actual-order \<ORDER\>

This command proposes to the primary an order (either “attack” or “retreat”). Here, the primary sends the order to the secondary nodes, and secondary nodes exchange messages to verify the proposed value. For each general, if the state is NF (Non-faulty), then generals work as expected just forwarding the proposed order between them. In contrast, if a general has a state F (Faulty), then each message that is exchanged with other generals is subject to (malicious) fluctuation between the proposed value and its counterpart. For instance, if the proposed value is “attack”, then when exchanging messages, the value oscillates between “attack” and “retreat” – the probability of selecting one choice over the other is equal 50/50).

After that, each general decides a final value based on the collected data, and a final quorum is performed to enforce the possible execution of the order.


### exit

This exits the program
