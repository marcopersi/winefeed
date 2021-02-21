package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.importers.Task;
import lombok.extern.slf4j.Slf4j;

import java.util.Set;

@Slf4j
public class SteinfelsImporter implements ImportingStrategy {

	private Set<Task> someTasks;

	public void setTasks(Set<Task> theTasks) {
		someTasks = theTasks;
	}

	@Override
	public void runImport() {

		for (Task aTask : someTasks) {
			// FIXME: guarantee run in 100% sequential order, start second only if first is done
			log.info("running task: {}", aTask);
			aTask.execute();
		}
		log.info("Import successfully done !");
	}

}
