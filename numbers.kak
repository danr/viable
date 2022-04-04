
try %{
    declare-user-mode numbers
}

def widen %{
    exec '<a-:>L<a-;>H<a-:>'
}
def unwiden %{
    exec '<a-:>H<a-;>L<a-:>'
}

def -params 2 on-one %{
    widen
    eval -draft %{
        exec %arg{1} <space>
        unwiden
        exec a %arg{2} <esc>|bc<ret>
    }
    unwiden
}

map global normal x 's(-?\d+\.\d+|-?\d+)<ret>: enter-user-mode -lock numbers<ret>'
map global numbers N -docstring -10 ': on-one "" -10 ; write<ret>'
map global numbers n -docstring -1  ': on-one "" -1  ; write<ret>'
map global numbers t -docstring +1  ': on-one "" +1  ; write<ret>'
map global numbers T -docstring +10 ': on-one "" +10 ; write<ret>'

map global numbers H -docstring -10 ': on-one  ( -10 ; write<ret>'
map global numbers h -docstring -1  ': on-one  ( -1  ; write<ret>'
map global numbers s -docstring +1  ': on-one  ( +1  ; write<ret>'
map global numbers S -docstring +10 ': on-one  ( +10 ; write<ret>'

map global numbers <a-N> -docstring -10 ': on-one (( -10 ; write<ret>'
map global numbers <a-n> -docstring -1  ': on-one (( -1  ; write<ret>'
map global numbers <a-t> -docstring +1  ': on-one (( +1  ; write<ret>'
map global numbers <a-T> -docstring +10 ': on-one (( +10 ; write<ret>'

map global numbers <a-H> -docstring -10 ': on-one ((( -10 ; write<ret>'
map global numbers <a-h> -docstring -1  ': on-one ((( -1  ; write<ret>'
map global numbers <a-s> -docstring +1  ': on-one ((( +1  ; write<ret>'
map global numbers <a-S> -docstring +10 ': on-one ((( +10 ; write<ret>'

