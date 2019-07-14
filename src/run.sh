#!/bin/bash
​
gnome-terminal --title="Simulation" --geometry 60x25+0+0 -e "python3 Simulation.py"
​
for i in {1..4} 
do
	port=$((5005+$i))
	gnome-terminal --title="Cliente $i" -e "python3 client.py -p $port" &
done