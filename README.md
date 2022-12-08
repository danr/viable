# viable

A viable alternative to frontend programming.

Viable updates outdated elements in the DOM using a DOM differ. It also
updates the values of input fields, with the exception of the currently
focused input field in the client. This allows for the sending of updates
to the backend on keystrokes to an input field.

In terms of session and variable values, the software uses session storage
to store state in the frontend. This is necessary because cookies are shared
between tabs, and session storage allows for duplication of tabs. If a new
tab is created, the session storage is empty and variables are initialized
with default values.

For persistent storage across windows and tabs in the browser, the software
also uses local storage. If a new tab or window is created and the value
of a variable is retrieved, the session storage is empty and the value from
the local storage is used instead. (Currently not implemented)

Cookies cannot be used for this because they have a maximum size of 4
kilobytes, whereas session and local storage have a minimum size in the order
of megabytes.
