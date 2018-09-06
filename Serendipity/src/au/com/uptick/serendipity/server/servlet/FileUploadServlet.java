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

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.lang.reflect.AccessibleObject;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;

import javax.servlet.ServletConfig;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.fileupload.FileItem;
import org.apache.commons.fileupload.FileUploadException;
import org.apache.commons.fileupload.disk.DiskFileItemFactory;
import org.apache.commons.fileupload.servlet.ServletFileUpload;
import org.apache.log4j.xml.DOMConfigurator;

import au.com.bytecode.opencsv.CSVReader;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Singleton;

@Singleton
@SuppressWarnings("serial")
public class FileUploadServlet extends HttpServlet {

  @Override
  public void doGet(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
    this.process(request, response);
  }

  @Override
  public void doPost(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
    this.process(request, response);
  }

  private void process(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    // check that we have a file upload request
    if (ServletFileUpload.isMultipartContent(request)) {
      processFiles(request, response);
    } else {
      processQuery(request, response);
    }
  }

  private File tmpDir;
  private static final String DESTINATION_DIR_PATH = "/files/upload";
  private File destinationDir;

  public void init(ServletConfig config) throws ServletException {
      super.init(config);

    DOMConfigurator.configure("log4j.xml");

    Log.debug("FileUpload Servlet");

    tmpDir = new File(((File) getServletContext().getAttribute("javax.servlet.context.tempdir")).toString());

    if (! tmpDir.isDirectory()) {
      throw new ServletException(tmpDir.toString() + " is not a directory");
    }

    Log.debug("tmpDir: " + tmpDir.toString());

    String realPath = getServletContext().getRealPath(DESTINATION_DIR_PATH);
    destinationDir = new File(realPath);

    if (! destinationDir.isDirectory()) {
      throw new ServletException(DESTINATION_DIR_PATH + " is not a directory");
    }

    Log.debug("destinationDir: " + destinationDir.toString());
  }

  private void processFiles(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {

    // create a factory for disk-based file items
    DiskFileItemFactory factory = new DiskFileItemFactory();

    // set the size threshold, above which content will be stored on disk
    factory.setSizeThreshold(1 * 1024 * 1024); // 1 MB

    // set the temporary directory (this is where files that exceed the threshold will be stored)
    factory.setRepository(tmpDir);

    // create a new file upload handler
    ServletFileUpload upload = new ServletFileUpload(factory);

    try {
      String recordType = "Account";

      // parse the request
      List items = upload.parseRequest(request);

      // process the uploaded items
      Iterator itr = items.iterator();

      while (itr.hasNext()) {
        FileItem item = (FileItem) itr.next();

        // process a regular form field
        if (item.isFormField()) {
          Log.debug("Field Name: " + item.getFieldName() + ", Value: " + item.getString());

          if (item.getFieldName().equals("recordType")) {
            recordType = item.getString();
          }
        } else { // process a file upload

          Log.debug("Field Name: " + item.getFieldName() + ", Value: " + item.getName() +
            ", Content Type: " + item.getContentType() + ", In Memory: " + item.isInMemory() +
            ", File Size: " + item.getSize());

          // write the uploaded file to the application's file staging area
          File file = new File(destinationDir, item.getName());
          item.write(file);

          // import the CSV file
          importCsvFile(recordType, file.getPath());
        }
      }
    } catch (FileUploadException e) {
      Log.error("Error encountered while parsing the request", e);
    } catch (Exception e) {
      Log.error("Error encountered while uploading file", e);
    }
  }

  private void processQuery(HttpServletRequest request, HttpServletResponse response)
      throws ServletException, IOException {
  }

  private void importCsvFile(String recordType, String filename) {

    try {
      // get the Class object for this recordType's DAO
      Class dao = getEntityDao(recordType);
      Object daoObject = createEntityDao(dao);

      // get the Class object for this recordType
      Class entity = getEntity(recordType);
      Field[] fields = entity.getDeclaredFields();

      // allow access to the Entities fields
      AccessibleObject.setAccessible(fields, true);

      // initialise the CSV Reader
      CSVReader reader = new CSVReader(new FileReader(filename));
      String [] nextLine;

      // process the first line in the file
      if ((nextLine = reader.readNext()) != null) {
        // build the HashMap of Field names
        getFieldNames(nextLine);
      }

      // process the file a line at a time
      while ((nextLine = reader.readNext()) != null) {
        persistEntity(daoObject, createEntity(entity, fields, nextLine));
      }
    } catch (ClassNotFoundException e) {
      Log.error("Error encountered while looking for class", e);
    } catch (FileNotFoundException e) {
      Log.error("Error encountered while reading file", e);
    } catch (Exception e) {
      Log.error("Error encountered while importing file", e);
    }
  }

  private static final int DEFAULT_HASH_MAP_CAPACITY = 100;
  private HashMap<String, Integer> fieldNames;

  private void getFieldNames(String [] nextLine) {
    fieldNames = new HashMap<String, Integer>(DEFAULT_HASH_MAP_CAPACITY);

    for (int i = 0; i < nextLine.length; i++) {
      // e.g. "accountName", 1
      fieldNames.put(nextLine[i].trim(), new Integer(i));
      Log.debug("Key: " + nextLine[i].trim() + " Value: " + i);
    }
  }

  private Object createEntity(Class entity, Field[] fields, String [] nextLine) {

    Log.debug("createEntity()");

    try {
      Object object = entity.newInstance();

      for (Field field : fields) {
        Class type = field.getType();

        // ignore Static fields
        if (Modifier.isStatic(field.getModifiers())) {
          continue;
        }

        if (type.getSimpleName().equals("String")) {
          Integer index = fieldNames.get(field.getName());
          if (index != null) {
            field.set(object, nextLine[index].trim());
            Log.debug("Field name: " + field.getName() + " index[" + index + "] = " + nextLine[index]);
          }
        } else if (type.getSimpleName().equals("List")) {

          List<Object> list = new ArrayList<Object>();

          Field declaredField = object.getClass().getDeclaredField(field.getName());
          Type genericType = declaredField.getGenericType();

          if (genericType instanceof ParameterizedType) {
            ParameterizedType pt = (ParameterizedType) genericType;
            Type [] t = pt.getActualTypeArguments();

            // e.g. "class au.com.uptick.serendipity.server.domain.Address"
            String className = t[0].toString().substring(6);
            Log.debug("className: " + className);

            Class nestedEntity = Class.forName(className);
            Field[] nestedFields = nestedEntity.getDeclaredFields();
            AccessibleObject.setAccessible(nestedFields, true);

            Object nestedObject = createNestedEntity(nestedEntity, nestedFields, nextLine);

            if (nestedObject != null) {
              list.add(nestedObject);
              field.set(object, list);
            }
          }
        }
      }

      // Log.debug(object.toString());

      return object;
    } catch (Exception e) {
      Log.error("Error encountered while creating entity", e);
    }

    return null;
  }

  private Object createNestedEntity(Class entity, Field[] fields, String [] nextLine) {

    Log.debug("createNestedEntity()");

    try {
      Object object = entity.newInstance();

      for (Field field : fields) {
        Class type = field.getType();

        // ignore Static fields
        if (Modifier.isStatic(field.getModifiers())) {
          continue;
        }

        if (type.getSimpleName().equals("String")) {
          Integer index = fieldNames.get(field.getName());
          if (index != null) {
            field.set(object, nextLine[index].trim());
            Log.debug("Field name: " + field.getName() + " index[" + index + "] = " + nextLine[index]);
          }
        }
      }

      return object;
    } catch (Exception e) {
      Log.error("Error encountered while creating nested entity", e);
    }

    return null;
  }

  private Object createEntityDao(Class dao) {

    try {
      return dao.newInstance();
    } catch (Exception e) {
      Log.error("Error encountered while creating entity dao", e);
    }

    return null;
  }

  private Long persistEntity(Object daoObject, Object entityObject) {

    Class[] parameterTypes = new Class[] {Object.class};

    try {
      Method method = daoObject.getClass().getMethod("createObject", parameterTypes);
      Object result = method.invoke(daoObject, new Object[] { entityObject });

      return (Long) result;
    } catch (SecurityException e) {
      Log.error("Security error encountered while persisting entity", e);
    } catch (NoSuchMethodException e) {
      Log.error("Method not found while persisting entity", e);
    } catch (Exception e) {
      Log.error("Error encountered while persisting entity", e);
    }

    return null;
  }

  private static Class getEntity(String name) throws ClassNotFoundException {
    return Class.forName("au.com.uptick.serendipity.server.domain." + name);
  }

  private static Class getEntityDao(String name) throws ClassNotFoundException {
    return Class.forName("au.com.uptick.serendipity.server.dao." + name + "Dao");
  }
}