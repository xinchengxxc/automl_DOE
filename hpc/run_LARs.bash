#!/bin/bash
set -e

#     𝐀      
#   / 𝐑 \     
#  // ⊂ \\    
#
# Quaerere. Cogita. Intellege.

# CPU Array Template


### Experiment base setup
EXPERIMENT_LAB="aghm"
EXPERIMENT_USER="u01233"
EXPERIMENT_NAME="automldoe"
EXPERIMENT_SCRIPT="run\ -\ xxc.py"

### Experiment specific parameters

### Apptainer settings
APPTAINER_FORCE_PULL=""
# APPTAINER_FORCE_PULL="--force"

### Docker registry
DOCKER_IMAGE_TAG="latest"
DOCKER_IMAGE_NAME="${EXPERIMENT_LAB}_${EXPERIMENT_USER}_${EXPERIMENT_NAME}"

### Container
CONTAINER_EXPERIMENT_BASE_PATH="/workspaces/automl_DOE"
CONTAINER_EXPERIMENT_SCRIPTS_PATH="${CONTAINER_EXPERIMENT_BASE_PATH}/python"

### Volumes
VOLUME_SRC_A="/home_cu/${EXPERIMENT_USER}/Projects/automl_DOE"
VOLUME_DST_A="${CONTAINER_EXPERIMENT_BASE_PATH}"

###############################################################################

### HPC job base setup

HPC_JOB_NAME="${DOCKER_IMAGE_NAME}"    # LAB_USER_EXPERIMENT
HPC_JOB_LOG="${DOCKER_IMAGE_NAME}.out" # job stdout
HPC_JOB_ERR="${DOCKER_IMAGE_NAME}.err" # job stderr
HPC_PARTITION="LARs-p0"                #

### HPC resources setup

HPC_MEM_PER_TASK="6G"               # max memory usage [G,M] on a node (512TiB arc-p1, 1TiB arc-p2)
HPC_CORES_PER_TASK="1"              # number of cores for a single task
HPC_THREADS_PER_CORE="1"            # 1 = disable Hyperthreading, 2 = enable Hyperthreading
HPC_ARRAY="0-285"                   # index of taskIDs to spawn tasks (has slurm configured hard limit!)
HPC_TASK_LIMIT="42"                 # hard task limit (arc-p0: 42C/84T)
HPC_NODES="1"                       # how many nodes a task can use
# HPC_TIME_LIMIT="01:00:00"           # max time limit

###############################################################################

# Create SBATCH
echo ".:⋮:. create sbatch..."
cat > ${EXPERIMENT_LAB}_${EXPERIMENT_USER}_${EXPERIMENT_NAME}.sbatch <<EOL
#!/bin/bash
#SBATCH --account=${EXPERIMENT_USER}
#SBATCH --job-name=${HPC_JOB_NAME}
#SBATCH --output=npc_${HPC_JOB_LOG}
#SBATCH --error=npc_${HPC_JOB_ERR}
#SBATCH --partition=${HPC_PARTITION}
#SBATCH --mem=${HPC_MEM_PER_TASK}
#SBATCH --array=${HPC_ARRAY}%${HPC_TASK_LIMIT}
#SBATCH --nodes=${HPC_NODES}

# restrict to 1 task only to pull container image
FILE_PATH="READY"

if [[ \$SLURM_ARRAY_TASK_ID -eq 0 ]]; then
    echo ".:⋮:. pull image + convert to sif on host \${HOSTNAME}..."
    apptainer pull docker://DT-IW-20-039:5000/${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}
    touch \${FILE_PATH}
fi

# wait until container image is ready
if [[ ! \$SLURM_ARRAY_TASK_ID -eq 0 ]]; then
    while [ ! -f "\${FILE_PATH}" ]; do
        echo -n "[\$SLURM_ARRAY_TASK_ID] "
        sleep 10
    done
fi

echo ".:⋮:. srun job array on \${HOSTNAME}"
srun --threads-per-core=${HPC_THREADS_PER_CORE} -o out/\${SLURM_ARRAY_TASK_ID}.out \
 apptainer exec \
 --pwd ${CONTAINER_EXPERIMENT_SCRIPTS_PATH} \
 --mount "type=bind,source=${VOLUME_SRC_A},destination=${VOLUME_DST_A}" \
 ${DOCKER_IMAGE_NAME}_${DOCKER_IMAGE_TAG}.sif \
 python3 ${EXPERIMENT_SCRIPT}

echo ".::. job finished"

# End of job script

EOL

### submit SBATCH to HPC
echo ".:⋮:. submit sbatch..."
sbatch ${EXPERIMENT_LAB}_${EXPERIMENT_USER}_${EXPERIMENT_NAME}.sbatch
