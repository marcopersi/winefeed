/**
 * (C) Copyright 2010, 2011 upTick Pty Ltd
 *
 * Licensed under the terms of the GNU General Public License version 3
 * as published by the Free Software Foundation. You may obtain a copy of the
 * License at: http://www.gnu.org/copyleft/gpl.html
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package au.com.uptick.serendipity.server.util;

import java.lang.reflect.*;
import java.util.*;

public class ObjectAnalyzer
{
  public static void printClass(String name)
  {
    try
    {
       // print class name and superclass name (if != Object)
       Class cl = Class.forName(name);
       Class supercl = cl.getSuperclass();
       String modifiers = Modifier.toString(cl.getModifiers());
       if (modifiers.length() > 0) System.out.print(modifiers + " ");
       System.out.print("class " + name);
       if (supercl != null && supercl != Object.class) System.out.print(" extends "
             + supercl.getName());

       System.out.print("\n{\n");
       printConstructors(cl);
       System.out.println();
       printMethods(cl);
       System.out.println();
       printFields(cl);
       System.out.println("}");
    }
    catch (ClassNotFoundException e)
    {
       e.printStackTrace();
    }
  }

  /**
   * Prints all constructors of a class
   * @param cl a class
   */

  public static void printConstructors(Class cl)
  {
     Constructor[] constructors = cl.getDeclaredConstructors();

     for (Constructor c : constructors)
     {
        String name = c.getName();
        System.out.print("   ");
        String modifiers = Modifier.toString(c.getModifiers());
        if (modifiers.length() > 0) System.out.print(modifiers + " ");
        System.out.print(name + "(");

        // print parameter types
        Class[] paramTypes = c.getParameterTypes();
        for (int j = 0; j < paramTypes.length; j++)
        {
           if (j > 0) System.out.print(", ");
           System.out.print(paramTypes[j].getName());
        }
        System.out.println(");");
     }
  }

  /**
   * Prints all methods of a class
   * @param cl a class
   */

  public static void printMethods(Class cl)
  {
     Method[] methods = cl.getDeclaredMethods();

     for (Method m : methods)
     {
        Class retType = m.getReturnType();
        String name = m.getName();

        System.out.print("   ");
        // print modifiers, return type and method name
        String modifiers = Modifier.toString(m.getModifiers());
        if (modifiers.length() > 0) System.out.print(modifiers + " ");
        System.out.print(retType.getName() + " " + name + "(");

        // print parameter types
        Class[] paramTypes = m.getParameterTypes();
        for (int j = 0; j < paramTypes.length; j++)
        {
           if (j > 0) System.out.print(", ");
           System.out.print(paramTypes[j].getName());
        }
        System.out.println(");");
     }
  }

  /**
   * Prints all fields of a class
   * @param cl a class
   */

  public static void printFields(Class cl)
  {
     Field[] fields = cl.getDeclaredFields();

     for (Field f : fields)
     {
        Class type = f.getType();
        String name = f.getName();
        System.out.print("   ");
        String modifiers = Modifier.toString(f.getModifiers());
        if (modifiers.length() > 0) System.out.print(modifiers + " ");
        System.out.println(type.getName() + " " + name + ";");
     }
  }

   /**
    * Converts an object to a string representation that lists all fields.
    * @param obj an object
    * @return a string with the object's class name and all field names and
    * values
    */

  public String toString(Object obj)
   {
      if (obj == null) return "null";
      if (visited.contains(obj)) return "...";
      visited.add(obj);
      Class cl = obj.getClass();
      if (cl == String.class) return (String) obj;
      if (cl.isArray())
      {
         String r = cl.getComponentType() + "[]{";
         for (int i = 0; i < Array.getLength(obj); i++)
         {
            if (i > 0) r += ",";
            Object val = Array.get(obj, i);
            if (cl.getComponentType().isPrimitive()) r += val;
            else r += toString(val);
         }
         return r + "}";
      }

      String r = cl.getName();
      // inspect the fields of this class and all superclasses
      do
      {
         r += "[";
         Field[] fields = cl.getDeclaredFields();
         AccessibleObject.setAccessible(fields, true);
         // get the names and values of all fields
         for (Field f : fields)
         {
            if (!Modifier.isStatic(f.getModifiers()))
            {
               if (!r.endsWith("[")) r += ",";
               r += f.getName() + "=";
               try
               {
                  Class t = f.getType();
                  Object val = f.get(obj);
                  if (t.isPrimitive()) r += val;
                  else r += toString(val);
               }
               catch (Exception e)
               {
                  e.printStackTrace();
               }
            }
         }
         r += "]";
         cl = cl.getSuperclass();
      }
      while (cl != null);

      return r;
   }

   private ArrayList<Object> visited = new ArrayList<Object>();
}
