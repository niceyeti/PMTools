echo "got $# args"
if [ "$#" -eq "2" ]; then
	echo "arg1 $1 arg2 $2"
fi

for var in "$@"; do
	echo var is $var
	if [[ $var == "--recurse="* ]]; then
		echo got recurse param $var
		recurseNo=$(echo $var | cut -f2 -d=)
		echo got recurse param $recurseNo
	fi
done


if [ $recurseNo -gt 0 ]; then
	echo recursing..
fi
