# IIC2523-T2-G06
IIC2523 - Sistemas Distribuidos - Pontificia Universidad Católica de Chile

## Integrantes

Nombre           | Mail
-------------    | -------------------
Benjamín Earle   | biearle@uc.cl
Christian Eilers | ceilers@uc.cl
Jorge Facuse     | jiperez11@uc.cl
Benjamín Lepe    | balepe@uc.cl
Mauro Mendoza    | msmendoza@uc.cl
Martín Ramírez   | mramirez7@uc.cl

## Environment settings
El **backend** de la aplicación fue desarrollado en Python 3.9. En primer lugar
se recomienda crear un `venv` para almacenar las dependencias de esta parte de
la tarea:

1. Donde gusten, pero una buena opción es el directorio raíz del proyecto, se
crea el `venv`:
```shell
python3 -m venv IIC2523_T1_backend
```

2. se selecciona
```shell
source IIC2523_T1_backend/bin/activate
```

3. lo actualizan
```shell
pip3 install -U pip setuptools wheel
```

4. y finalmente instalan las dependencias de esta parte de la tarea:
```shell
pip3 install -r requerimentes.txt
```
