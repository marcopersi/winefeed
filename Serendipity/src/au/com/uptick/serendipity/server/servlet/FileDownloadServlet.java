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

package au.com.uptick.serendipity.server.servlet;

import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.AccessibleObject;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.Iterator;
import java.util.List;

import javax.servlet.ServletConfig;
import javax.servlet.ServletException;
import javax.servlet.ServletOutputStream;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import au.com.bytecode.opencsv.CSVWriter;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Singleton;

@Singleton
@SuppressWarnings("serial")
public class FileDownloadServlet extends HttpServlet {

  private static final String RECORD_TYPE = "recordType";
  // private static final String CONTENT_TYPE = "text/plain";
  private static final String CONTENT_TYPE = "application/x-download";
  // private static final String FILENAME = "Accounts.csv";

  @Override
  public void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
    this.processRequest(request, response);
  }

  @Override
  public void doPost(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
    this.processRequest(request, response);
  }

  private static final String DESTINATION_DIR_PATH = "/files/download";
  private File destinationDir;

  public void init(ServletConfig config) throws ServletException {
      super.init(config);

    // DOMConfigurator.configure("log4j.xml");

    Log.debug("FileDownload Servlet");

    String realPath = getServletContext().getRealPath(DESTINATION_DIR_PATH);
    destinationDir = new File(realPath);

    if (! destinationDir.isDirectory()) {
      throw new ServletException(DESTINATION_DIR_PATH + " is not a directory");
    }

    Log.debug("destinationDir: " + destinationDir.toString());
  }

  private void processRequest(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    Log.info("FileDownloadServlet Servlet");

    String recordType = request.getParameter(RECORD_TYPE);

    File file = new File(destinationDir, recordType + "s.csv");

    Log.debug("file.getPath(): " + file.getPath());

    createCsvFile(recordType, file.getPath());

    ServletOutputStream outputStream = response.getOutputStream();
    response.setContentType(CONTENT_TYPE);
    response.setContentLength((int) file.length());
    response.setHeader("Content-Disposition", "attachment; filename=" + recordType + "s.csv");

    byte[] buffer = new byte[8 * 1024]; // 8k buffer
    DataInputStream inputStream = new DataInputStream(new FileInputStream(file));
    int length = 0;

    try {
      while ((inputStream != null) && ((length = inputStream.read(buffer)) != -1)) {
        outputStream.write(buffer, 0, length);
      }
    } catch (Exception e) {
      StringWriter stringWriter = new StringWriter();
      PrintWriter printWriter = new PrintWriter(stringWriter);
      e.printStackTrace(printWriter);
      response.setContentType("text/plain");
      response.getOutputStream().print(stringWriter.toString());
    } finally {
      inputStream.close();
      outputStream.flush();
      outputStream.close();
    }
  }

  @SuppressWarnings("unchecked")
  private void createCsvFile(String recordType, String filename) {

    Log.debug("createCsvFile()");

    try {
      Class dao = getEntityDao(recordType);
      Object daoObject = createEntityDao(dao);

      Class entity = getEntity(recordType);
      Field[] fields = entity.getDeclaredFields();
      AccessibleObject.setAccessible(fields, true);

      CSVWriter writer = new CSVWriter(new FileWriter(filename));
      String [] nextLine = null;

      List<Object> objects = retrieveObjects(daoObject);
      Iterator iterator = objects.iterator();

      if (iterator.hasNext()) {
        nextLine = getFieldNames(iterator.next(), fields);
      }

      // write Field names as the first line in the file
      writer.writeNext(nextLine);

      for (Object object : objects) {

        String fieldValues = new String();

        for (Field field : fields) {
          String value = new String();
          Class type = field.getType();

          if (Modifier.isStatic(field.getModifiers())) {
            continue;
          }

          // ignore Primary Key field
          if (type.getSimpleName().equals("Long")) {
            continue;
          }

          if (type.getSimpleName().equals("String")) {
            value = getValue(object, field);
            Log.debug("Field name: " + field.getName() + " value: " + value);
          } else if (type.getSimpleName().equals("List")) {

            Class nestedEntity = Class.forName(getClassName(object, field));
            Field[] nestedFields = nestedEntity.getDeclaredFields();
            AccessibleObject.setAccessible(nestedFields, true);

            // List<Object> nestedObjects = getList(object, field);
            List<Object> nestedObjects = (List<Object>) field.get(object);
            Iterator nestedIterator = nestedObjects.iterator();

            if (nestedIterator.hasNext()) {
              value = getNestedValues(nestedIterator.next(), nestedFields);
            }
          }

          fieldValues += value;
        }

        Log.debug("fieldValues: " + fieldValues);

        nextLine = fieldValues.split("#");
        writer.writeNext(nextLine);
      }

      writer.close();
    } catch (ClassNotFoundException e) {
      Log.error("Error encountered while looking for class", e);
    } catch (FileNotFoundException e) {
      Log.error("Error encountered while reading file", e);
    } catch (Exception e) {
      Log.error("Error encountered while exporting file", e);
    }
  }

  private String getClassName(Object object, Field field) {

    String className = new String();

    try {
      Field declaredField = object.getClass().getDeclaredField(field.getName());
      Type genericType = declaredField.getGenericType();

      if (genericType instanceof ParameterizedType) {
        ParameterizedType pt = (ParameterizedType) genericType;
        Type [] t = pt.getActualTypeArguments();

        // e.g. "class au.com.uptick.serendipity.server.domain.Address"
        className = t[0].toString().substring(6);
      }
    } catch (SecurityException e) {
      Log.error("Security error encountered while retrieving objects", e);
    } catch (NoSuchFieldException e) {
      Log.error("Field not found while retrieving objects", e);
    } catch (Exception e) {
      Log.error("Error encountered while retrieving objects", e);
    }

    Log.debug("className: " + className);

    return className;
  }

  private String [] getFieldNames(Object object, Field[] fields) {

    Log.debug("getFieldNames()");

    String fieldNames = new String();

    try {
      for (Field field : fields) {
        Class type = field.getType();

        if (Modifier.isStatic(field.getModifiers())) {
          continue;
        }

        if (type.getSimpleName().equals("String")) {
          fieldNames += field.getName() + "#";
        } else if (type.getSimpleName().equals("List")) {

          Class nestedEntity = Class.forName(getClassName(object, field));
          Field[] nestedFields = nestedEntity.getDeclaredFields();
          AccessibleObject.setAccessible(nestedFields, true);

          fieldNames += getNestedFieldNames(nestedEntity, nestedFields);
        }
      }
    } catch (Exception e) {
      Log.error("Error encountered while exporting file", e);
    }

    Log.debug("fieldNames: " + fieldNames);

    return fieldNames.split("#");
  }

  private String getNestedFieldNames(Class entity, Field[] fields) {

    Log.debug("getNestedFieldNames()");

    String fieldNames = new String();

    try {
      for (Field field : fields) {
        Class type = field.getType();

        if (Modifier.isStatic(field.getModifiers())) {
          continue;
        }

        if (type.getSimpleName().equals("String")) {
          fieldNames += field.getName() + "#";
        }
      }
    } catch (Exception e) {
      Log.error("Error encountered while obtaining nested entity field names", e);
    }

    return fieldNames;
  }

  private String getValue(Object object, Field field) {

    String value = new String();

    try {
      value = (String) field.get(object);
      value += "#";
    } catch (IllegalAccessException e) {
      Log.error("Error encountered while accessing file", e);
    } catch (Exception e) {
      Log.error("Error encountered while exporting file", e);
    }

    return value;
  }

  private String getNestedValues(Object object, Field[] fields) {

    Log.debug("getNestedValues()");

    String values = new String();

    try {
      for (Field field : fields) {
        Class type = field.getType();

        if (Modifier.isStatic(field.getModifiers())) {
          continue;
        }

        if (type.getSimpleName().equals("String")) {
          values += ((String) field.get(object)) + "#";
        }
      }
    } catch (Exception e) {
      Log.error("Error encountered while obtaining nested entity field values", e);
    }

    return values;
  }

  private static Class getEntityDao(String name) throws ClassNotFoundException {
    return Class.forName("au.com.uptick.serendipity.server.dao." + name + "Dao");
  }

  private static Class getEntity(String name) throws ClassNotFoundException {
    return Class.forName("au.com.uptick.serendipity.server.domain." + name);
  }

  private Object createEntityDao(Class dao) {

    try {
      return dao.newInstance();
    } catch (Exception e) {
      Log.error("Error encountered while creating entity dao", e);
    }

    return null;
  }

  @SuppressWarnings("unchecked")
  private List<Object> retrieveObjects(Object daoObject) {

    Log.debug("retrieveObjects()");

    Class[] parameterTypes = new Class[2];
    parameterTypes[0] = Integer.TYPE;
    parameterTypes[1] = Integer.TYPE;

    try {
      Method method = daoObject.getClass().getMethod("retrieveObjects", parameterTypes);
      Object result = method.invoke(daoObject, new Object[] { 50, 0 });

      return (List<Object>) result;
    } catch (SecurityException e) {
      Log.error("Security error encountered while retrieving objects", e);
    } catch (NoSuchMethodException e) {
      Log.error("Method not found while retrieving objects", e);
    } catch (Exception e) {
      Log.error("Error encountered while retrieving objects", e);
    }

    return null;
  }
}
