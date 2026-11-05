
## Putting the count on the icon

The decision — how many conversations are stopped waiting for a person
— and the act of painting it are separate functions, for the reason the
service worker gives for the same split: this is among the hardest code
here to observe once it is running, and the worst place to find out a
rule was wrong.

Clearing, never setting zero. A zero still paints a mark in some
browsers, and a mark that does not go away is why somebody stops
reading it — including on the day it was right.

Every failure is swallowed, and the rejection case is the one that was
not. Most browsers have no badging at all; the calls that exist return
promises that can be refused; and this runs on every state change. A
rejected call left unhandled is an unhandled rejection on every turn,
in the console, about a feature nobody asked about — and the console is
where somebody looks when something else is wrong.
