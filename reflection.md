# Reflection

## What I got wrong at the start

At first i thought IIITA had proper registry for different concerns like visitors and hostel staff. But once i checked with the registry Satyajit gave me i saw cooler, AC, carpenter, laundry, visitors everything just dumped into one single book with a mix of hindi and english words! That's when i realised transcribing those messy pages into queriable data is very useful.

## What I would cut

So if i had to actually implement this for a hostel desk i would cut the extra flags like late hour and fancy ASCII tabe formatting and stick to a simple look up for categories in the initial shipping!

## Where AI helped

Antigravity definitely saved a lot of time writing the messy code like date/time parsing, regex grouping for hindi/English and bad row data warnings using just the python's standard library!

## Where AI wasted time

Initially it created research.md in the parent Fire AI folder instead of inside BH4-register-audit so i hato move it in! Also initially in audit.py it silently added 24 hours wheneer out_time was earlier than in_time which actually hid the bad timestamps until i caught that and forced it to properly log warnings. Also some early write-ups sounded a bit too formal and i had to re-write them properly!