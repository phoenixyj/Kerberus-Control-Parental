#!/bin/bash
echo "*******************************************************************"
echo "*******************************************************************"
echo "Inicio de los tests"
for file in *Test.py;do 
  echo ""
  echo "===================================================================="
  echo "Test del módulo $file"
  echo "===================================================================="
  echo ""
  python $file -v;done
echo "*******************************************************************"
echo "*******************************************************************"