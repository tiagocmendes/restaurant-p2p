#!/bin/bash
​
r=$((RANDOM%4))
gnome-terminal --title="Simulation" --geometry 60x25+0+0 -e "python3 Simulation.py -ft $r -r 1"



for i in {1..2} 
do	

	r_client=$((5100+$r))
	port=$((5005+$i))
	
	
	gnome-terminal --title="Cliente $i" -e "python3 client.py -r $r_client -p $port" &
done