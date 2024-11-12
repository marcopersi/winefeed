package ch.persi.java.vino.importers.weinboerse;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.importers.Task;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;

public class WeinboerseImporter implements ImportingStrategy {

    private final Logger log = LoggerFactory.getLogger(getClass());
    private Set<Task> someTasks;

    public void setTasks(Set<Task> theTasks) {
        someTasks = theTasks;
    }

    @Override
    public void runImport() {

        for (Task aTask : someTasks) {
            // FIXME: guarantee run in 100% sequential order, start second only if first is done
            log.info("running task {}", aTask);
            aTask.execute();
        }
        log.info("Import successfully done !");
    }

}
